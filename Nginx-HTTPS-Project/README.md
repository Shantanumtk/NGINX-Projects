# Nginx HTTPS with Self‑Signed Certificate on AWS EC2

A GitHub‑ready, step‑by‑step guide to configure **HTTPS (TLS)** with a **self‑signed certificate** on **Ubuntu 22.04 (EC2)** using **Nginx**, enforcing **HTTP → HTTPS** redirect.

> ⚠️ Self‑signed certificates are for **testing/practice** only. Browsers will warn. For production, use a trusted CA (e.g., Let’s Encrypt/ACM).

---

## 📂 Repository Structure

```
nginx-https-selfsigned/
├── README.md                 # This tutorial
├── nginx/
│   └── default               # Nginx site configuration (with placeholders)
└── ssl/                      # (Optional) Keep sample cert/key here if you commit mock files
    ├── selfsigned.crt        # Not used in prod; you will generate real ones on the server
    └── selfsigned.key
```

> You will **generate certs on the EC2 instance** under `/etc/ssl/selfsigned/` — the `ssl/` folder is only a placeholder so the repo layout is clear.

---

## ✅ What You’ll Get
- HTTPS served by Nginx on port **443** (self‑signed)
- Global **HTTP → HTTPS** redirect on port **80**
- Minimal, readable config you can reuse

---

## 1) Prerequisites
- EC2 instance: **Ubuntu 22.04 LTS**
- Security Group inbound rules: `22/tcp`, `80/tcp`, `443/tcp`
- Your instance public DNS (example throughout: `ec2-3-88-239-217.compute-1.amazonaws.com`)
- SSH access to the instance

(Optional but recommended) Allocate an **Elastic IP** and associate it to the instance.

---

## 2) Set Hostname Variable (on your EC2)
```bash
export HOST="ec2-3-88-239-217.compute-1.amazonaws.com"
```
Replace the value with your EC2 public DNS if different. You can confirm with:
```bash
echo $HOST
```

---

## 3) Install Nginx & OpenSSL
```bash
sudo apt update
sudo apt -y install nginx openssl
sudo systemctl enable --now nginx
```

---

## 4) Generate a Self‑Signed Certificate (on the server)
Create a dedicated directory and generate cert/key valid for 365 days:
```bash
sudo mkdir -p /etc/ssl/selfsigned
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "/etc/ssl/selfsigned/$HOST.key" \
  -out "/etc/ssl/selfsigned/$HOST.crt" \
  -subj "/CN=$HOST"
sudo chmod 600 "/etc/ssl/selfsigned/$HOST.key"
```

---

## 5) Place the Nginx Site Config
Create the site file **on your EC2** at `/etc/nginx/sites-available/default` using this template with placeholders. (If you cloned this repo, you can `sudo cp nginx/default /etc/nginx/sites-available/default` and then replace placeholders.)

**Template contents (uses `__HOST__` placeholder):**
```nginx
# /etc/nginx/sites-available/default

# 1) HTTP: redirect all requests to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name __HOST__;

    return 301 https://$host$request_uri;
}

# 2) HTTPS: serve site with self-signed cert
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name __HOST__;

    ssl_certificate     /etc/ssl/selfsigned/__HOST__.crt;
    ssl_certificate_key /etc/ssl/selfsigned/__HOST__.key;

    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    # Optional hardening:
    # ssl_protocols TLSv1.2 TLSv1.3;

    root /var/www/html;
    index index.html;
}
```

**Replace placeholders with your `$HOST`:**
```bash
sudo sed -i "s/__HOST__/$HOST/g" /etc/nginx/sites-available/default
```

**Validate & reload Nginx:**
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 6) Add a Test Page (optional)
```bash
echo "Hello HTTPS (self-signed)!" | sudo tee /var/www/html/index.html >/dev/null
```

---

## 7) Verify
**Redirect (should be 301 to https):**
```bash
curl -I "http://$HOST"
```

**HTTPS (ignore warning with `-k`):**
```bash
curl -kI "https://$HOST"
```

**Cert summary:**
```bash
echo | openssl s_client -connect "$HOST:443" -servername "$HOST" 2>/dev/null | openssl x509 -noout -subject -issuer -dates
```

Open a browser:
- `http://$HOST` → redirects to HTTPS
- `https://$HOST` → browser shows a warning (expected for self‑signed) → proceed to view page

---

## 8) Maintenance
**Renew the self‑signed cert before 365 days:**
```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "/etc/ssl/selfsigned/$HOST.key" \
  -out "/etc/ssl/selfsigned/$HOST.crt" \
  -subj "/CN=$HOST"
sudo systemctl reload nginx
```

**Always validate config before reload:**
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## ✅ Checklist
- [ ] Port 80 → **301** to HTTPS
- [ ] Port 443 serves site (warning is expected)
- [ ] `openssl` shows subject/issuer/dates
- [ ] Nginx config passes `nginx -t`

---

## Appendix A — `nginx/default` (ready to commit)
If you want to keep the config in the repo and copy it during deployment, use this file at `nginx/default` **exactly** as below. It uses a placeholder so it’s portable across hosts.

```nginx
# nginx/default (commit this file in the repo)

server {
    listen 80;
    listen [::]:80;
    server_name __HOST__;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name __HOST__;

    ssl_certificate     /etc/ssl/selfsigned/__HOST__.crt;
    ssl_certificate_key /etc/ssl/selfsigned/__HOST__.key;

    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;

    root /var/www/html;
    index index.html;
}
```

**Deployment snippet** (copy config and replace placeholder):
```bash
sudo cp nginx/default /etc/nginx/sites-available/default
sudo sed -i "s/__HOST__/$HOST/g" /etc/nginx/sites-available/default
sudo nginx -t && sudo systemctl reload nginx
```

---

## Appendix B — Why self‑signed? (quick note)
- Good for learning Nginx TLS, redirects, and config layout.
- Not trusted by browsers (you’ll see a warning). For public sites, switch to a CA‑issued cert without changing the Nginx structure.
