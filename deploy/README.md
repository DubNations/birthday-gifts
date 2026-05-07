# Birthday Gifts deployment

This directory contains sample production deployment assets for Nginx, systemd, and SQLite backups.

## 1. Configure environment

Copy `.env.example` to `/opt/birthday-gifts/.env` and set production values:

- `DATABASE_URL`: database connection string, for example `sqlite:///./gift.db`.
- `ADMIN_PASSWORD`: required administrator login password. The old `admin123` default is rejected at startup.
- `ADMIN_TOKEN_SECRET`: optional but recommended signing secret for admin bearer tokens.
- `CORS_ORIGINS`: comma-separated HTTPS origins allowed to call the API, for example `https://example.com,https://www.example.com`.
- `LOCK_TIMEOUT_MINUTES`: minutes before locked gifts are released.
- `MAX_REGRET_CHANCES`: how many regret/release actions a participant may use.

## 2. Build and install the frontend

```bash
cd /opt/birthday-gifts/frontend
npm ci
npm run build
```

The Nginx config serves `/opt/birthday-gifts/frontend/dist` at `/` and falls back to `index.html` for the SPA.

## 3. Run the backend with systemd

```bash
cd /opt/birthday-gifts/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
sudo cp /opt/birthday-gifts/deploy/systemd/birthday-gifts.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now birthday-gifts.service
```

The service binds FastAPI to `127.0.0.1:8000`; Nginx proxies `/api/` to that backend.

## 4. Configure HTTPS Nginx

1. Replace `example.com` in `deploy/nginx/birthday-gifts.conf` with your real domain.
2. Obtain a certificate, for example with Certbot:

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d example.com -d www.example.com
```

3. Install and reload Nginx:

```bash
sudo cp /opt/birthday-gifts/deploy/nginx/birthday-gifts.conf /etc/nginx/sites-available/birthday-gifts.conf
sudo ln -sf /etc/nginx/sites-available/birthday-gifts.conf /etc/nginx/sites-enabled/birthday-gifts.conf
sudo nginx -t
sudo systemctl reload nginx
```

The HTTP server redirects to HTTPS. `/` serves `frontend/dist`, and `/api/` reverse proxies to FastAPI.

## 5. Enable scheduled SQLite backups

```bash
sudo cp /opt/birthday-gifts/deploy/systemd/birthday-gifts-backup.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now birthday-gifts-backup.timer
```

By default backups run daily at 03:00 UTC and write timestamped copies of `gift.db` to `/opt/birthday-gifts/backups`. The script keeps 30 days of `gift_*.db` snapshots. The admin reset endpoint also creates an automatic `pre_reset` snapshot before mutating data.
