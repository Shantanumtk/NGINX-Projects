# VPC + Nginx Reverse Proxy + 2 FastAPI App EC2s

This project demonstrates how to build a secure AWS network architecture with a custom VPC, a public Nginx reverse proxy EC2, and two private FastAPI application EC2s. Traffic flows through Nginx, which load balances requests across the FastAPI instances in private subnets. A NAT Gateway is used to allow the private EC2s to download system and Python packages without exposing them to the internet.

---

## 📂 Directory Structure

```
aws-fastapi-nginx-vpc/
├── README.md
├── fastapi/
│   ├── main.py              # FastAPI app code
│   └── fastapi.service      # systemd service unit for uvicorn
└── nginx/
    └── fastapi.conf         # Nginx reverse proxy + load balancing config
```

---

## 🏗️ Architecture Overview

* **VPC** – isolated private network (`10.0.0.0/16`)
* **Public Subnet** – contains Nginx EC2 (reverse proxy, public IP)
* **Private Subnet** – contains two FastAPI EC2s (reachable only from Nginx on port 8000)
* **Internet Gateway (IGW)** – allows inbound/outbound internet traffic for the public subnet
* **NAT Gateway** – enables outbound-only internet access from private subnet
* **Route Tables**

  * Public Subnet → IGW
  * Private Subnet → NAT Gateway → IGW

Traffic flow:

```
Internet → IGW → Public Subnet → Nginx EC2 → Private Subnet → FastAPI EC2s
```

---

## 🔧 1. Create VPC and Networking

### Create VPC

* Name: `fastapi-vpc`
* IPv4 CIDR: `10.0.0.0/16`

### Create Subnets

* **Public subnet**

  * Name: `public-subnet`
  * CIDR: `10.0.1.0/24`
  * AZ: `us-east-1a` (example)
  * Enable auto-assign public IPv4

* **Private subnet**

  * Name: `private-subnet`
  * CIDR: `10.0.2.0/24`
  * AZ: `us-east-1a`

### Create Internet Gateway (IGW)

* Name: `fastapi-igw`
* Attach to `fastapi-vpc`

### Route Tables

* **Public Route Table**

  * Name: `public-rt`
  * Routes:

    * `10.0.0.0/16 → local`
    * `0.0.0.0/0 → fastapi-igw`
  * Associate with `public-subnet`

* **Private Route Table**

  * Name: `private-rt`
  * Routes:

    * `10.0.0.0/16 → local`
  * Associate with `private-subnet`

---

## 🔐 2. Security Groups

* **SG-NGINX** (for Nginx EC2)

  * Inbound:

    * SSH (22) → your IP
    * HTTP (80) → 0.0.0.0/0

* **SG-APP** (for FastAPI EC2s)

  * Inbound:

    * TCP (8000) → Source: SG-NGINX

---

## 💻 3. Launch EC2 Instances

* **Nginx EC2 (public)**

  * AMI: Ubuntu 22.04
  * Subnet: `public-subnet`
  * Public IP: enabled
  * SG: SG-NGINX
  * Name: `nginx-ec2`

* **FastAPI EC2 #1 & #2 (private)**

  * AMI: Ubuntu 22.04
  * Subnet: `private-subnet`
  * Public IP: disabled
  * SG: SG-APP
  * Names: `fastapi-app-1`, `fastapi-app-2`

---

## 🌐 4. NAT Gateway Setup

1. **Allocate an Elastic IP**

   * Console → EC2 → Elastic IPs → Allocate Elastic IP → Scope: VPC

2. **Create a NAT Gateway**

   * Console → VPC → NAT Gateways → Create NAT Gateway
   * Name: `fastapi-nat`
   * Subnet: `public-subnet`
   * Elastic IP: the one you allocated
   * Wait until status = Available

3. **Update Private Route Table**

   * Console → VPC → Route Tables → `private-rt`
   * Edit routes → add:

     * Destination: `0.0.0.0/0`
     * Target: `fastapi-nat`

4. **Confirm Route Tables**

   * **Public Subnet RT**

     ```
     10.0.0.0/16 → local
     0.0.0.0/0   → IGW
     ```
   * **Private Subnet RT**

     ```
     10.0.0.0/16 → local
     0.0.0.0/0   → NAT Gateway
     ```

5. **Verify from private EC2s**

   ```bash
   ping -c 2 google.com
   curl -I https://archive.ubuntu.com
   sudo apt update && sudo apt -y install python3-venv python3-pip
   ```

---

## ⚙️ 5. Install FastAPI on App EC2s

On **both app EC2s**:

```bash
sudo apt update && sudo apt -y install python3-pip python3-venv
sudo mkdir -p /opt/fastapi && sudo chown ubuntu:ubuntu /opt/fastapi
cd /opt/fastapi
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn[standard]
```

Create `/opt/fastapi/main.py`:

```python
from fastapi import FastAPI
import socket

app = FastAPI()
HOST = socket.gethostname()

@app.get("/")
def root():
    return {"message": "Hello from FastAPI behind Nginx!", "host": HOST}

@app.get("/healthz")
def health():
    return {"ok": True, "host": HOST}
```

Create systemd service `/etc/systemd/system/fastapi.service`:

```ini
[Unit]
Description=FastAPI app (uvicorn)
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/fastapi
ExecStart=/opt/fastapi/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable + start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable fastapi
sudo systemctl start fastapi
```

---

## 🌍 6. Configure Nginx (public EC2)

On **Nginx EC2**:

```bash
sudo apt update && sudo apt -y install nginx
```

Create `/etc/nginx/sites-available/fastapi.conf`:

```nginx
upstream fastapi_backend {
    least_conn;
    server 10.0.2.10:8000 max_fails=3 fail_timeout=30s;   # app1 private IP
    server 10.0.2.11:8000 max_fails=3 fail_timeout=30s;   # app2 private IP
    keepalive 64;
}

server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://fastapi_backend;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection        "";
    }
}
```

Enable config:

```bash
sudo ln -sf /etc/nginx/sites-available/fastapi.conf /etc/nginx/sites-enabled/fastapi.conf
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

---

## ✅ 7. Test

From your laptop:

```bash
curl http://<Nginx_Public_IP>/
curl http://<Nginx_Public_IP>/
```

You should see alternating responses:

```json
{"message":"Hello from FastAPI behind Nginx!","host":"ip-10-0-2-10"}
{"message":"Hello from FastAPI behind Nginx!","host":"ip-10-0-2-11"}
```

---

## Result

* **Public subnet** → Nginx EC2 (internet-facing)
* **Private subnet** → Two FastAPI EC2s (only accessible via Nginx)
* **NAT Gateway** → enables outbound internet for private EC2s
* **Nginx upstream** → load balancing between private FastAPI apps

This is a secure, scalable AWS setup for serving FastAPI apps behind Nginx.
