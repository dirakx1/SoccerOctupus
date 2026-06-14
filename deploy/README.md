# SoccerOctupus Deployment Guide

This is the production deployment runbook for SoccerOctupus on an Ubuntu EC2 instance.

It covers the full setup we settled on:

- Domain: `socceroctupus.co`
- Optional alias: `www.socceroctupus.co`
- Server IP: `54.162.149.159`
- App path: `/var/www/SoccerOctupus`
- Frontend: Vue/Vite static build in `frontend/dist`
- Backend: Flask app on `127.0.0.1:5002`
- Reverse proxy: Nginx
- Process manager: `systemd`
- SSL: Certbot

## Final Architecture

Public traffic flow:

```text
Browser
  -> Nginx (:80 / :443)
  -> Frontend static files from /var/www/SoccerOctupus/frontend/dist
  -> /api/* proxied to 127.0.0.1:5002
  -> Flask backend
```

Important ports:

- `80`: public HTTP, redirect and Certbot validation
- `443`: public HTTPS
- `5002`: backend only, should stay private

## Final Server Settings

Use these final values in production:

```text
Domain:        socceroctupus.co
WWW alias:     www.socceroctupus.co
Server IP:     54.162.149.159
Project path:  /var/www/SoccerOctupus
Frontend root: /var/www/SoccerOctupus/frontend/dist
Backend bind:  127.0.0.1:5002
Service name:  socceroctupus-backend
Nginx site:    /etc/nginx/sites-available/socceroctupus
```

## 1. DNS Setup

Create these DNS records:

```text
A     socceroctupus.co       54.162.149.159
A     www.socceroctupus.co   54.162.149.159
```

You can verify DNS from your machine with:

```bash
dig +short socceroctupus.co
dig +short www.socceroctupus.co
```

Both should resolve to:

```text
54.162.149.159
```

## 2. EC2 / Firewall Requirements

Make sure your EC2 security group allows:

- TCP `80` from the internet
- TCP `443` from the internet

If you use UFW on the server, allow:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

Do not expose `5002` publicly.

## 3. Install System Packages

On Ubuntu:

```bash
sudo apt update
sudo apt install -y nginx python3 python3-venv python3-pip nodejs npm snapd
```

Recommended Python version: `3.11+`

## 4. Put The App On The Server

Create the deployment directory:

```bash
sudo mkdir -p /var/www
sudo chown -R "$USER":"$USER" /var/www
cd /var/www
```

Clone the repository:

```bash
git clone <your-repo-url> SoccerOctupus
cd /var/www/SoccerOctupus
```

If the app is already somewhere else, move or copy it into:

```text
/var/www/SoccerOctupus
```

This path matters because Nginx is configured to serve from:

```text
/var/www/SoccerOctupus/frontend/dist
```

Using `/var/www` avoids the permission problems you hit when serving from `/home/ubuntu/...`.

## 5. Backend Environment File

Create:

```bash
cd /var/www/SoccerOctupus/backend
nano .env
```

Example `.env`:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/socceroctupus
CLERK_SECRET_KEY=
CLERK_PUBLISHABLE_KEY=
CLERK_JWKS_URL=https://api.clerk.com/v1/jwks
CLERK_WEBHOOK_SECRET=
FRONTEND_ORIGIN=https://socceroctupus.co

DEBUG=false
PORT=5002

LLM_API_KEY=
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o

YOUTUBE_API_KEY=
OPTA_API_KEY=
ZEP_API_KEY=
ZEP_GRAPH_ID=
```

Notes:

- `PORT=5002` should stay as is
- Most external API keys are optional
- The app can still run with fallback behavior when keys are missing
- `DATABASE_URL` should point at Postgres in production
- Clerk secrets stay in env; only non-secret model preferences move into the admin UI

## 6. Install Backend Dependencies

```bash
cd /var/www/SoccerOctupus/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
venv/bin/python -m alembic upgrade head
```

Before granting admin access, sign in once through the deployed app so Clerk
sync creates the local `users` row, then promote the first admin manually in
Postgres:

```sql
UPDATE users SET is_admin = true WHERE email = '<admin-email>';
```

Also configure a Clerk webhook to `POST https://socceroctupus.co/api/webhooks/clerk`
with the matching `CLERK_WEBHOOK_SECRET`.

## 7. Test Backend Locally

Start the backend manually once:

```bash
cd /var/www/SoccerOctupus/backend
source venv/bin/activate
python run.py
```

In another shell:

```bash
curl http://127.0.0.1:5002/health
curl http://127.0.0.1:5002/api/predictions/groups
```

Expected `health` response:

```json
{"service":"FifaOctopus","status":"ok"}
```

If both work, stop the manual server and continue.

## 8. Create The systemd Service

Create the service file:

```bash
sudo nano /etc/systemd/system/socceroctupus-backend.service
```

Paste this:

```ini
[Unit]
Description=SoccerOctupus Flask Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/SoccerOctupus/backend
EnvironmentFile=-/var/www/SoccerOctupus/backend/.env
ExecStart=/var/www/SoccerOctupus/backend/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:5002 run:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Set ownership so `www-data` can read the app and write runtime outputs:

```bash
sudo chown -R www-data:www-data /var/www/SoccerOctupus
```

Start and enable the backend:

```bash
sudo systemctl daemon-reload
sudo systemctl enable socceroctupus-backend
sudo systemctl start socceroctupus-backend
sudo systemctl status socceroctupus-backend
```

Useful backend log command:

```bash
sudo journalctl -u socceroctupus-backend -f
```

## 9. Build The Frontend

```bash
cd /var/www/SoccerOctupus/frontend
npm ci
npm run build
```

You should end up with:

```text
/var/www/SoccerOctupus/frontend/dist/index.html
/var/www/SoccerOctupus/frontend/dist/assets/
```

Sanity check:

```bash
ls -la /var/www/SoccerOctupus/frontend/dist
```

## 10. Nginx Config

The repo already contains the production Nginx site config:

```text
deploy/nginx/socceroctupus.conf
```

Current config values:

- `server_name socceroctupus.co www.socceroctupus.co;`
- `root /var/www/SoccerOctupus/frontend/dist;`
- `/api/*` proxied to `127.0.0.1:5002`

Install it:

```bash
sudo cp /var/www/SoccerOctupus/deploy/nginx/socceroctupus.conf /etc/nginx/sites-available/socceroctupus
sudo ln -sf /etc/nginx/sites-available/socceroctupus /etc/nginx/sites-enabled/socceroctupus
```

If the default site is enabled, remove it:

```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

Test and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 11. Test HTTP Before SSL

From the server:

```bash
curl -I http://127.0.0.1:5002/health
curl -I http://socceroctupus.co/
curl -I http://socceroctupus.co/api/predictions/groups
```

From your browser:

```text
http://socceroctupus.co/
```

At this stage:

- frontend should load
- `/health` should work
- `/api/predictions/groups` should work

## 12. Install Certbot

Use the snap-based Certbot install:

```bash
sudo apt update
sudo apt install -y snapd
sudo snap install core
sudo snap refresh core

sudo apt remove -y certbot python3-certbot-nginx
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot
```

Check Nginx before issuing the cert:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 13. Issue SSL Certificate

For root domain and `www`:

```bash
sudo certbot --nginx -d socceroctupus.co -d www.socceroctupus.co
```

If you only want the root domain:

```bash
sudo certbot --nginx -d socceroctupus.co
```

Then test renewal:

```bash
sudo certbot renew --dry-run
```

After SSL is active, the site should work at:

```text
https://socceroctupus.co/
```

Keep both ports open:

- `80` for redirect and certificate renewal
- `443` for HTTPS traffic

## 14. Update Flow For New Deployments

Whenever you deploy new code:

```bash
cd /var/www/SoccerOctupus
git pull

cd frontend
npm ci
npm run build

cd ../backend
source venv/bin/activate
pip install -r requirements.txt

sudo systemctl restart socceroctupus-backend
sudo nginx -t
sudo systemctl reload nginx
```

## 15. Troubleshooting

### Backend checks

```bash
curl http://127.0.0.1:5002/health
curl http://127.0.0.1:5002/api/predictions/groups
sudo systemctl status socceroctupus-backend
sudo journalctl -u socceroctupus-backend -f
```

### Nginx checks

```bash
sudo nginx -t
sudo tail -f /var/log/nginx/socceroctupus.error.log
sudo tail -f /var/log/nginx/socceroctupus.access.log
```

### Common problems

- `404` on `/api/*`
  - Nginx site not enabled
  - Nginx not reloaded after config change

- `502 Bad Gateway`
  - backend is not running on `127.0.0.1:5002`
  - `systemd` service failed to start

- Frontend loads badly or assets missing
  - `npm run build` not run
  - wrong `root` path in Nginx

- Vue routes return `404`
  - `location /` must include:

```nginx
try_files $uri $uri/ /index.html;
```

- `500 Internal Server Error` with `Permission denied` on `index.html`
  - this happened when serving from `/home/ubuntu/...`
  - final fix is to serve from:

```text
/var/www/SoccerOctupus/frontend/dist
```

- Domain works but SSL issuance fails
  - DNS not propagated yet
  - port `80` blocked in EC2 security group
  - Nginx config invalid

## Reference Files

- Nginx site config: [deploy/nginx/socceroctupus.conf](/Users/shaharyarbabar/Documents/Freelancing/reokreok/SoccerOctupus/deploy/nginx/socceroctupus.conf)
- Deployment guide: [deploy/README.md](/Users/shaharyarbabar/Documents/Freelancing/reokreok/SoccerOctupus/deploy/README.md)
