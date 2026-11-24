# Active plan: Raspberry Pi deployment instructions

## Objective

Document a reproducible Raspberry Pi OS deployment by cloning the repository into `/mnt/ssd/git/virtual-index-card`, running Gunicorn with an ASGI worker on `127.0.0.1:10001` under systemd, and proxying through Nginx with Certbot/Let's Encrypt HTTPS. Provide practical update, diagnostics, backup/restore and renewal guidance. No remote deployment is authorized.

## Scope / assumptions

- **In scope:** `docs/raspberry-pi-deployment.md`, README link, minimum locked runtime dependencies for the documented Gunicorn command, local smoke checks.
- **Out of scope:** provisioning a real Pi/domain/SSD, changing app auth or SQLite schema, declaring `BL-013`, `BL-016`, `BL-022` or `BL-023` complete without security/deployment/restore verification. Those items remain open.
- Assumes a Debian-based Raspberry Pi OS (64-bit recommended), Python 3.11+, working SSD mount and DNS name pointing to the Pi's public IP with forwarded TCP 80/443. The requested **10001 is the loopback app port**, not the browser HTTPS port (443). Certbot requires a real domain; no certificate is issued for a bare private IP.
- Risk: published documentation is a recipe, not a tested deployment. Gunicorn is installed in the app's locked production environment; systemd uses the venv binary directly. SQLite must remain on persistent SSD storage outside `git` maintenance, with off-device backups and a tested restore before public exposure.

## Tasks

| # | Task | Status |
|---|---|---|
| 1 | Check runtime/dependencies and plan secure topology and permissions | Completed |
| 2 | Add and lock Gunicorn ASGI worker dependencies; validate install and local startup | Completed |
| 3 | Write Pi guide for clone, systemd, Nginx, Certbot, backups/restore, updates, verification | Completed |
| 4 | Update README, review commands/doc consistency, run tests and diff checks | Completed |

## Acceptance criteria

- [x] Guide covers exact clone path, uv setup, production sync, service user and writable SQLite path, systemd Gunicorn on `127.0.0.1:10001`, Nginx proxy, Certbot certificate issuance/renewal, firewall/router prerequisites, validation, updates and troubleshooting.
- [x] A locked install provides the exact worker and server executable in the guide; local Gunicorn /health smoke check passes.
- [x] Backup/restore guidance avoids unsafe live file copies; public exposure is clearly gated on TLS, security review and tested off-device backups.
- [x] `uv run pytest -q`, `git diff --check` and documentation review pass; real Pi/TLS/restore tests are explicitly unverified.

## Related backlog

`BL-013` (pre-exposure security review), `BL-016` (repeatable deployment package), `BL-022` (HTTPS reverse-proxy deployment), and `BL-023` (automated backups/restore drill) remain Ready. This documentation slice does not meet their live-deployment acceptance criteria.

## Progress log

- 2026-11-24: Reviewed repository instructions, active plan/backlog, architecture, runtime config and dependency manifest; clean branch `arena/bd203bc7-virtual-index-card`. Selected internal port 10001 behind Nginx 443 and explicit SQLite SSD permissions. No secrets or domain assumed.
- Added `gunicorn` and `uvicorn-worker` with uv; updated `pyproject.toml` and `uv.lock`. `uv sync --no-dev --locked --python /usr/bin/python3` installed production dependencies; started the exact Gunicorn/ASGI command bound to loopback `:10001`, verified `/health` returned `{"status":"ok"}` and `/login` returned 200, then stopped it. Restored development dependencies with `uv sync --group dev --locked`.
- Wrote `docs/raspberry-pi-deployment.md` with Pi setup, branch clone, service/SSD permissions, systemd, Nginx, Certbot, backups/restore, updates and diagnostics; linked it from `README.md`. `uv run pytest -q`: 25 passed, 1 existing Starlette/httpx deprecation warning. `git diff --check`: passed. Actual Pi installation, public DNS/TLS, renewal, threat review and backup restore drill were not run; `BL-013`, `BL-016`, `BL-022` and `BL-023` remain open. No commit, push or live deployment requested.
