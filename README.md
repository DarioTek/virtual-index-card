# virtual-index-card

A hosted web application for personal index cards. Each approved account can create multiple private decks, named sequentially by default (`My Deck 1`, `My Deck 2`, ...), or give them unique custom names and rename them later. Write notes on a card's front and back, flip between them, and add/edit/delete cards. The management page lists newest-created cards first; in Review mode you can shuffle the selected deck, and that review order persists across reloads.

New accounts are **created by an administrator**: visitors submit an account request, an administrator approves it, and the system issues the account name and password to hand to the user.

All durable data — accounts, sessions, decks, cards, and per-deck card order — is stored in **SQLite**.

## Features

- Administrator-approved accounts: visitors request an account; an administrator approves or rejects the request and receives the new account's credentials to deliver out of band.
- Individual accounts with login and logout.
- Administrator role with an account-request queue, one-time credential display, password reset (which signs the user out everywhere), a **Users page listing every account** with delete (permanent) and reset actions, an **Admin profile page** to update the administrator's username and password (current password required; other sessions are signed out), and a first-admin bootstrap command/env vars.
- Multiple private decks per account with sequential defaults or unique custom names; owners can rename decks and permanently delete empty non-last decks, while users cannot see or modify another account's decks or cards.
- Add, edit, delete, and flip cards on the management page, newest-created first.
- Review mode: one card at a time, tap to flip, cycle through the saved deck order, or shuffle from Review (returns to card 1). The shuffled order survives reloads; the management page remains newest-first.
- Read-only public links: `GET /s/{token}` renders one deck for anonymous visitors with no mutation routes, `no-store` caching, and `noindex` headers.
- Rich-text card formatting on both front and back with keyboard-accessible toolbar controls for **bold**, **italic**, **underline**, and a fixed WCAG AA 4-color palette (`black`, `green`, `red`, `blue`), supporting overlapping styles, a 5,000 visible Unicode code-point limit per side, safe server-side canonicalization/escaping, and verbatim preservation of plain-text cards.
- **Public read-only deck links**: an owner can create, rotate, and revoke an unlisted link that shows one deck to visitors without an account. The token is stored only as a SHA-256 hash and displayed once.
- **Versioned JSON export** of a single owned deck (`/decks/{id}/export.json`) that preserves formatting and Review order.
- CSRF-protected writes and hashed passwords/session tokens.

## Prerequisites

- Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

## Install

```bash
uv sync --group dev
```

This creates `.venv` and installs the locked dependencies from `uv.lock`.

## Run locally

```bash
VIC_DATABASE_PATH=./data/virtual-index-card.sqlite3 \
  uv run uvicorn virtual_index_card.app:app --reload --host 0.0.0.0 --port 10001
```

Bootstrap the first administrator (the CLI creates the account or promotes an existing one and prints a generated temporary password once):

```bash
VIC_DATABASE_PATH=./data/virtual-index-card.sqlite3 \
  uv run python -m virtual_index_card.create_admin admin
```

Then open <http://127.0.0.1:10001> and log in. Visitors use **Request an account** on the login page; the administrator reviews requests at **Admin → Account requests**, and on approval the page shows the account name and temporary password once. New users can log in with those credentials. The SQLite file is created automatically on first start and is ignored by Git.

Configuration is read from the environment, and a local `.env` file is loaded when present (copy [`.env.example`](.env.example) to `.env`). Real environment variables always win. All settings are optional:

| Variable | Default | Purpose |
|---|---|---|
| `VIC_DATABASE_PATH` | `data/virtual-index-card.sqlite3` | Location of the SQLite database |
| `VIC_SESSION_TTL_SECONDS` | `604800` | Session lifetime in seconds |
| `VIC_COOKIE_SECURE` | `false` | Set to `true` when serving over HTTPS |
| `VIC_ENABLE_DOCS` | `false` | Set to `true` to expose the interactive API docs at `/docs`, `/redoc`, and `/openapi.json`; leave `false` in production |
| `VIC_MAX_EXPORT_ROWS` | `10000` | Maximum cards in one JSON export; larger decks get HTTP 413 |
| `VIC_MAX_EXPORT_BYTES` | `1048576` | Maximum size of one JSON export in bytes; larger exports get HTTP 413 |
| `VIC_ADMIN_USERNAME` | _(unset)_ | Optional administrator bootstrap on every startup: ensure this account exists with the admin role |
| `VIC_ADMIN_PASSWORD` | _(unset)_ | Password for the bootstrap account; required to create a missing admin, optional when promoting an existing user. Reapplies on each start — unset it afterwards if you do not want the password re-pinned |

## Test

```bash
uv run pytest -q
```

The suite prints one Starlette/httpx deprecation warning (`httpx` is being replaced by `httpx2` in Starlette's test client); it does not affect any test.

The standard validation set for a change is `uv run pytest -q`, `uv run python -m compileall -q src tests`, `node --check src/virtual_index_card/static/app.js`, and `git diff --check`.

## Project layout

```text
src/virtual_index_card/
  app.py          FastAPI routes, auth, admin approval queue + user management, API, and templates
  admin.py        ensure_admin() shared by the CLI and env bootstrap
  create_admin.py `python -m virtual_index_card.create_admin` CLI
  config.py       Environment-based settings
  db.py           SQLite connection, schema version 5, and v1 → v2 → v3 → v4 → v5 migrations
  domain.py       Card model, validation, username/password rules, Fisher–Yates shuffle
  formatting.py   Rich-text document allowlist validation, visible-length checks, and safe HTML rendering
  repository.py   User-scoped SQLite queries, account requests, and deck shares
  security.py     Password hashing, temporary-password generation, token helpers
  templates/      Jinja pages and shared card/editor macros
  static/         Flip interaction, rich-text editor toolbar, fetch-based API calls, CSS
tests/            Unit and integration tests
uv.lock           Locked dependency versions
```

## Deployment notes

See the [Raspberry Pi deployment runbook](docs/raspberry-pi-deployment.md) for cloning `main` onto `/mnt/ssd/git/virtual-index-card`, running Gunicorn on loopback port **10001** under systemd, and putting Nginx/Certbot in front of it, and [`docs/operations.md`](docs/operations.md) for the background start/stop scripts and process layout. The runbook has not been verified on a Pi: HTTPS/reverse-proxy validation and scheduled off-device SQLite backups with a restore drill remain open. Set `VIC_COOKIE_SECURE=true` only when the app is served over HTTPS.

## Documentation

- [`PLAN.md`](PLAN.md) — implementation record for completed assignments and the active plan.
- Open and proposed follow-up work is tracked through GitHub Issues; see [`PLAN.md`](PLAN.md) for the active assignment.
- [`docs/architecture.md`](docs/architecture.md) — as-built architecture.
- [`docs/technical-decisions.md`](docs/technical-decisions.md) — decisions and rationale.
- [`docs/operations.md`](docs/operations.md) — background start/stop scripts, PID/log files, and runtime layout.
- [`docs/raspberry-pi-deployment.md`](docs/raspberry-pi-deployment.md) — Raspberry Pi operator runbook (not yet tested on a Pi).
- [`AGENTS.md`](AGENTS.md) — repository operating instructions.
- [`AGENT_PROMPTS.md`](AGENT_PROMPTS.md) — copy-and-paste prompts for working with `AGENTS.md` and `PLAN.md`.
