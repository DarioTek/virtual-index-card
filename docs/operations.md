# Operations: running the app as a background process

This page covers the repository's start/stop scripts and the runtime files they create. For a full production deployment (systemd, Nginx, TLS, backups), use the [Raspberry Pi deployment runbook](raspberry-pi-deployment.md) instead — that runbook does **not** use these scripts and instead runs Gunicorn under systemd.

## Scripts

| File | Purpose |
|---|---|
| `virtual-index-card-start.sh` | Starts Gunicorn with Uvicorn workers in the background, writing a PID file and a log file |
| `virtual-index-card-stop.sh` | Stops the process recorded in the PID file |

Both scripts are written for the deployment host and assume the project lives at `/mnt/ssd/git/virtual-index-card`; edit `PROJECT_DIR` at the top of each if your checkout is elsewhere. They also export `TZ=America/New_York` and `VIC_DATABASE_PATH=./data/virtual-index-card.sqlite3`.

## Configuration files

Settings come from the environment, and a `.env` file in the working directory is loaded automatically when present (copy [`.env.example`](../.env.example) to `.env`). Precedence is: real environment variable → `.env` → built-in default. Because the scripts `cd` into `PROJECT_DIR` and run from there, a `.env` next to `pyproject.toml` is the one that applies. The systemd unit uses `EnvironmentFile=` instead, which wins over `.env`, so the two setups do not conflict.

## What start creates

```text
/mnt/ssd/git/virtual-index-card/
├── data/virtual-index-card.sqlite3     SQLite database (created on first start, ignored by Git)
├── gunicorn.pid                        PID of the running master process
└── logs/virtual_index_card.log         Combined Gunicorn stdout/stderr
```

## How it binds

The script starts Gunicorn on **`127.0.0.1:10001`**:

```bash
uv run gunicorn virtual_index_card.app:app \
  --workers 2 \
  --worker-class uvicorn_worker.UvicornWorker \
  --bind 127.0.0.1:10001
```

Loopback binding is deliberate: port 10001 is the application port, not a public one. Put Nginx (or another reverse proxy) in front of it as described in the [runbook](raspberry-pi-deployment.md#5-configure-nginx-and-issue-a-lets-encrypt-certificate), and never forward 10001 from the router.

The worker class is `uvicorn_worker.UvicornWorker` from the `uvicorn-worker` package, which is a runtime dependency. The older `uvicorn.workers.UvicornWorker` path still imports but emits a `DeprecationWarning`.

## Usage

```bash
./virtual-index-card-start.sh
curl -fsS http://127.0.0.1:10001/health   # {"status":"ok"}
cat logs/virtual_index_card.log
./virtual-index-card-stop.sh
```

If the stop script reports a missing PID file, find the process directly:

```bash
pgrep -f "gunicorn.*virtual_index_card.app:app"
kill <PID>
```

## Difference from the systemd setup

The runbook's systemd unit and these scripts are alternative ways to run the same application:

| | Scripts | systemd unit |
|---|---|---|
| Process manager | `nohup` + PID file | systemd |
| Workers | 2 | 1 by default |
| Restart on failure | No | `Restart=on-failure` |
| Bind address | `127.0.0.1:10001` | `127.0.0.1:10001` |
| Logs | `logs/virtual_index_card.log` | `journalctl -u virtual-index-card` |

Use systemd for anything long-lived; the scripts are convenient for a manual restart on the same host.
