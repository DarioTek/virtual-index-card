# Deploy on Raspberry Pi OS (Gunicorn + Nginx + Let's Encrypt)

This is an **operator runbook**, not a record of a completed deployment. It assumes Raspberry Pi OS (Debian-based, 64-bit recommended) with Python 3.11+, a persistent SSD mounted at `/mnt/ssd`, and a real public DNS name. Replace `cards.example.com` throughout with your own domain **before running any commands**.

Traffic flows as follows:

```text
Browser -- HTTPS :443 --> Nginx -- HTTP loopback :10001 --> Gunicorn/ASGI --> SQLite on SSD
             HTTP :80 --> redirect to HTTPS (also used for certificate validation)
```

**Port 10001 is the application port on `127.0.0.1`, not a public port.** Do not forward 10001 on the router or bind Gunicorn to `0.0.0.0`. Public users visit `https://cards.example.com/` on port 443. Let's Encrypt cannot issue an HTTP-01 certificate for a private/LAN IP address; use a public DNS name and reachable port 80. A reverse tunnel or DNS-01 challenge is a different setup and is not covered here.

## 1. Prerequisites and networking

- Provision a stable Pi OS installation, non-root account with `sudo`, correct system clock, reliable SSD mount, and power/network connectivity. Check `findmnt /mnt/ssd`; ensure the SSD is mounted automatically on reboot (for example via its UUID in `/etc/fstab`) **before proceeding**. Do not use an unmounted `/mnt/ssd` path: the app could silently create a second database on the SD card.
- Point an **A record** for `cards.example.com` at the public IPv4 address. If you also publish an AAAA record, IPv6 must reach this Pi as well. For a home connection, forward TCP **80 and 443** to the Pi and allow them in the host firewall (if enabled); do **not** forward 10001. Check for CGNAT/ISP port blocks if certificate issuance fails. Keep SSH accessible before changing firewall rules.
- Install the basics:

  ```bash
  sudo apt update
  sudo apt install -y git curl python3 python3-venv nginx certbot python3-certbot-nginx sqlite3
  python3 --version          # must be 3.11 or newer
  findmnt /mnt/ssd            # must show the SSD mount
  ```

- Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for the deployment account (review the upstream installer if required by your security policy):

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  uv --version
  ```

## 2. Clone and install the production dependencies

The application is on the `main` branch. Run these commands as the non-root deployment account, not as the service account:

```bash
sudo mkdir -p /mnt/ssd/git
sudo chown "$USER:$(id -gn)" /mnt/ssd/git   # only if this directory is yours to administer
git clone --branch main --single-branch \
  https://github.com/DarioTek/virtual-index-card.git \
  /mnt/ssd/git/virtual-index-card
cd /mnt/ssd/git/virtual-index-card
uv sync --no-dev --locked --python /usr/bin/python3
.venv/bin/gunicorn --version
```

`uv sync --no-dev --locked` installs the locked runtime dependencies (including Gunicorn and `uvicorn-worker`) into `.venv` and rejects an out-of-date lockfile. Using the system Python keeps the virtual environment independent of the deployment user's home directory. If `/mnt/ssd/git` already has other owners, arrange access without recursively changing ownership of other repositories. The code and `.venv` must be readable/traversable by the service user, but that user should not be able to write source files.

## 3. Dedicated service user, SQLite storage and environment

Create a service user and writable **SSD** data directory. The application creates its SQLite schema on first startup; never commit this file. If you have an existing database, copy it into this directory **while the app is stopped**, set ownership to `vic`, and back it up first.

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin vic
sudo install -d -o vic -g vic -m 0700 /mnt/ssd/git/virtual-index-card/data
sudo -u vic test -x /mnt/ssd/git/virtual-index-card
sudo -u vic test -x /mnt/ssd/git/virtual-index-card/.venv/bin/gunicorn
```

If `vic` already exists, skip `useradd`; if the `test` commands fail, check permissions on **every parent directory** with `namei -l /mnt/ssd/git/virtual-index-card/.venv/bin/gunicorn` and grant the minimum traversal/read access needed (not write access to code). The service will not start if its SSD directory is not writable.

Create `/etc/virtual-index-card.env` (there are no application secrets to paste here):

```bash
sudo install -o root -g vic -m 0640 /dev/null /etc/virtual-index-card.env
sudo tee /etc/virtual-index-card.env >/dev/null <<'EOF'
VIC_DATABASE_PATH=/mnt/ssd/git/virtual-index-card/data/virtual-index-card.sqlite3
VIC_COOKIE_SECURE=true
VIC_SESSION_TTL_SECONDS=604800
# Optional one-time bootstrap of the first administrator (see section 5):
# VIC_ADMIN_USERNAME=admin
# VIC_ADMIN_PASSWORD=change-me-and-remove-afterwards
EOF
```

`VIC_COOKIE_SECURE=true` means sign-in cookies work only over HTTPS; do not request/approve accounts or log in over plain HTTP. Keep the SQLite file and the environment file out of Git.

## 4. Run Gunicorn as a systemd service on port 10001

Create `/etc/systemd/system/virtual-index-card.service`:

```ini
[Unit]
Description=Virtual Index Card (Gunicorn ASGI)
After=network-online.target
Wants=network-online.target
RequiresMountsFor=/mnt/ssd/git/virtual-index-card/data

[Service]
Type=simple
User=vic
Group=vic
WorkingDirectory=/mnt/ssd/git/virtual-index-card
EnvironmentFile=/etc/virtual-index-card.env
ExecStart=/mnt/ssd/git/virtual-index-card/.venv/bin/gunicorn --workers 1 --worker-class uvicorn_worker.UvicornWorker --bind 127.0.0.1:10001 virtual_index_card.app:app
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/mnt/ssd/git/virtual-index-card/data

[Install]
WantedBy=multi-user.target
```

Use **one worker** initially for a small Pi/SQLite deployment; measure load before increasing concurrency. `RequiresMountsFor` makes systemd wait for the SSD mount. The code is read-only to the service, and only its `data` directory is writable.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now virtual-index-card
sudo systemctl status virtual-index-card --no-pager
curl -fsS http://127.0.0.1:10001/health   # {"status":"ok"}
sudo ss -ltnp | grep 10001               # must show 127.0.0.1:10001, not 0.0.0.0
```

On failure: `sudo journalctl -u virtual-index-card -n 100 --no-pager`. Ensure `findmnt /mnt/ssd` succeeds, `.venv` is readable by `vic`, and the SQLite directory is owned by `vic`.

## 5. Configure Nginx and issue a Let's Encrypt certificate

Replace the domain and create `/etc/nginx/sites-available/virtual-index-card`:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name cards.example.com;

    location / {
        proxy_pass http://127.0.0.1:10001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site (remove the Nginx default site only if it is not used for anything else):

```bash
sudo ln -s /etc/nginx/sites-available/virtual-index-card /etc/nginx/sites-enabled/virtual-index-card
sudo nginx -t
sudo systemctl reload nginx
```

Ensure port 80 is reachable from the internet before requesting a certificate. Certbot's Nginx plugin edits this site to add TLS and an HTTP-to-HTTPS redirect:

```bash
sudo certbot --nginx -d cards.example.com --redirect
sudo nginx -t
sudo systemctl reload nginx
sudo certbot renew --dry-run
```

Inspect `/etc/nginx/sites-available/virtual-index-card` afterward: the HTTPS `server` block must still proxy to `http://127.0.0.1:10001`; HTTP must redirect to HTTPS. Add these headers **inside the HTTPS server block** (not just the HTTP redirect block), then test/reload Nginx again:

```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
# Optional after HTTPS is verified and you are ready to commit to HTTPS:
add_header Strict-Transport-Security "max-age=31536000" always;
```

If you use a firewall, allow inbound TCP 80/443 while retaining your SSH access. Do not allow 10001 from outside. Certbot normally installs a renewal timer; check `systemctl list-timers | grep certbot` and repeat `sudo certbot renew --dry-run` after firewall, router, or DNS changes. Renewals need port 80 reachable for HTTP-01 validation.

Verify from a different machine/network (not only the Pi):

```bash
curl -I http://cards.example.com/            # 301/308 redirect to https://
curl -i https://cards.example.com/health   # HTTP 200, {"status":"ok"}
curl -sS -D - -o /dev/null https://cards.example.com/login  # GET: HTTP 200 and security headers
```

Then test the account-request flow, login, card CRUD and Review over **HTTPS** in a browser: visitors can only file an account request — accounts are created when the administrator approves them at **Admin → Requests** (page title *Account requests*), and the system issues a shown-once account name/temporary password. Bootstrap the first administrator before exposing the service: either set `VIC_ADMIN_USERNAME`/`VIC_ADMIN_PASSWORD` in the environment file for one deploy (then remove them; the password reapplies on every start otherwise), or run `sudo -u vic .venv/bin/python -m virtual_index_card.create_admin admin` on the Pi and note the generated password. There is no email verification or login rate limiting yet; mail-based delivery of credentials is still open backlog work. Assess this exposure and complete a threat/privacy review before publishing personal notes. If the proxy gives 502, check `journalctl -u virtual-index-card` and Nginx error logs. If Certbot fails, check public DNS resolution, port forwarding, firewall, IPv6 AAAA (if present), and `sudo nginx -t`.

## 6. Backups and restore (required before public exposure)

SQLite contains all accounts, sessions, notes and ordering. Do **not** use `cp` on a live database as a backup. Use SQLite's online `.backup`, verify the result, and copy backups to a **different disk or remote destination** (a directory on the same SSD does not protect against SSD failure). Backups contain personal notes and password hashes: restrict access. For example, after attaching a separate backup disk mounted at `/mnt/backup` and making a private directory writable by `vic`:

```bash
findmnt /mnt/backup
sudo install -d -o vic -g vic -m 0700 /mnt/backup/virtual-index-card
DB=/mnt/ssd/git/virtual-index-card/data/virtual-index-card.sqlite3
BACKUP=/mnt/backup/virtual-index-card/virtual-index-card-$(date -u +%Y%m%dT%H%M%SZ).sqlite3
sudo -u vic test -f "$DB"
sudo -u vic sqlite3 "$DB" ".backup '$BACKUP'"
sudo -u vic sqlite3 "$BACKUP" 'PRAGMA integrity_check;'  # must print ok
```

Automate this with a monitored daily systemd timer or cron job that **fails if `/mnt/backup` is not mounted**, runs `.backup` as `vic`, verifies `integrity_check`, and logs/alerts on failure. Retain multiple generations and copy them off-site; verify the schedule, retention, and alerts on the actual Pi. This guide does **not** create or validate a backup timer for you (scheduled off-device backups remain open backlog work).

To practice restoring, use a **separate test copy/location** first. For a real restore, stop the service and back up the current DB before replacing it; do not overwrite a running SQLite database:

```bash
sudo systemctl stop virtual-index-card
# Replace BACKUP below with the chosen verified backup file on the separate disk.
BACKUP=/mnt/backup/virtual-index-card/CHOSEN-BACKUP.sqlite3
DB=/mnt/ssd/git/virtual-index-card/data/virtual-index-card.sqlite3
sudo sqlite3 "$BACKUP" 'PRAGMA integrity_check;'  # must print ok
sudo -u vic sqlite3 "$DB" ".backup '${DB}.pre-restore.sqlite3'"  # recovery snapshot
sudo mv "$DB" "${DB}.pre-restore-original"
# Keep any old sidecars with the old database, never mix them with the restored file.
for suffix in -wal -shm -journal; do
  if sudo test -e "${DB}${suffix}"; then
    sudo mv "${DB}${suffix}" "${DB}${suffix}.pre-restore-original"
  fi
done
sudo install -o vic -g vic -m 0600 "$BACKUP" "$DB"
sudo systemctl start virtual-index-card
curl -fsS http://127.0.0.1:10001/health
```

If the original DB has WAL/journal sidecars, keep them together with the original database as above; never mix them with a restored main file. Validate restored user/card data, not just `/health`, and keep the recovery files until you are satisfied. Complete a real restore drill and off-device backup verification before exposing private notes publicly.

## 7. Updates and diagnostics

With the deployment account, take a verified backup first. Stop the service so it cannot import half-updated code; then pull the latest `main` and locked dependencies:

```bash
sudo systemctl stop virtual-index-card
cd /mnt/ssd/git/virtual-index-card
git status --short
git pull --ff-only origin main
uv sync --no-dev --locked --python /usr/bin/python3
sudo systemctl start virtual-index-card
sudo systemctl status virtual-index-card --no-pager
curl -fsS http://127.0.0.1:10001/health
```

If `git status --short` is nonempty, investigate before pulling; don't reset local changes or overwrite the DB. Check `sudo journalctl -u virtual-index-card -f`, `sudo tail -f /var/log/nginx/error.log`, and `sudo certbot certificates` when troubleshooting. Keep Pi OS packages, uv, Python and the app dependencies patched. If the code changes the SQLite schema in a future release, arrange a migration and backup before updating.

**Unverified here:** real Raspberry Pi installation, public DNS/port forwarding, certificate issuance/renewal, hardened reverse proxy, automatic off-device backups, and a restore drill. The corresponding backlog items (Pi installation validation, HTTPS/reverse-proxy validation, and off-device backup automation with a restore drill) remain open until validated on the deployment target.
