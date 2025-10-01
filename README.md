# NGINX-Projects (AWS)

Small, copy‑pasteable NGINX setups for EC2.

> Target: **Ubuntu 22.04 LTS**

---

## 📂 Projects

1. **Reverse Proxy + 2 FastAPI Apps**
   Public NGINX EC2 (public subnet) → two FastAPI EC2s (private subnet). Load-balanced with `upstream`.

2. **HTTPS (Self‑Signed) + Redirect**
   NGINX on 443 with a self‑signed cert and global HTTP→HTTPS.

---

## 🚀 Quickstart

### Reverse Proxy (high level)

* VPC `10.0.0.0/16`; subnets: public `10.0.1.0/24`, private `10.0.2.0/24`
* IGW attached; NAT GW in public subnet
* SG‑NGINX: allow **22** (your IP), **80** (0.0.0.0/0)
* SG‑APP: allow **8000** (source = SG‑NGINX)
* On NGINX EC2, point `fastapi.conf` to the **private IPs** of both apps and reload NGINX.

**Test:** `curl http://<NGINX_PUBLIC_IP>/`

### HTTPS (Self‑Signed)

```bash
export HOST="ec2-xx-xx-xx-xx.compute-1.amazonaws.com"
sudo apt update && sudo apt -y install nginx openssl && sudo systemctl enable --now nginx
sudo mkdir -p /etc/ssl/selfsigned
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "/etc/ssl/selfsigned/$HOST.key" -out "/etc/ssl/selfsigned/$HOST.crt" -subj "/CN=$HOST"
sudo chmod 600 "/etc/ssl/selfsigned/$HOST.key"
sudo cp Nginx-HTTPS-Project/nginx-files/default /etc/nginx/sites-available/default
sudo sed -i "s/__HOST__/$HOST/g" /etc/nginx/sites-available/default
sudo nginx -t && sudo systemctl reload nginx
```

**Verify:** `curl -I http://$HOST` (301) • `curl -kI https://$HOST`

> ⚠️ Self‑signed is for **testing**. Use Let’s Encrypt/ACM for prod.

---

## 🗂 Structure

```
NGINX-Projects/
├─ Nginx-Reverse-Proxy-Project/
│  ├─ fastapi/
│  └─ nginx/
└─ Nginx-HTTPS-Project/
   └─ nginx-files/
```

## 🩺 Troubleshooting

* NGINX: `sudo nginx -t` • `sudo systemctl status nginx`
* Apps: `curl http://10.0.2.10:8000/healthz` • `curl http://10.0.2.11:8000/healthz`

## 📄 License

Add a license (e.g., MIT) at repo root.
