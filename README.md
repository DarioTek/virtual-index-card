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
- Rich-text card formatting on both front and back with keyboard-accessible toolbar controls for **bold**, **italic**, **underline**, **block quotes**, and a fixed WCAG AA 6-color palette (`black`, `green`, `red`, `orange`, `blue`, `pink`), supporting overlapping styles, a 5,000 visible Unicode code-point limit per side, safe server-side canonicalization/escaping, and verbatim preservation of plain-text cards.
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

Configuration (all optional):

| Variable | Default | Purpose |
|---|---|---|
| `VIC_DATABASE_PATH` | `data/virtual-index-card.sqlite3` | Location of the SQLite database |
| `VIC_SESSION_TTL_SECONDS` | `604800` | Session lifetime in seconds |
| `VIC_COOKIE_SECURE` | `false` | Set to `true` when serving over HTTPS |
| `VIC_ADMIN_USERNAME` | _(unset)_ | Optional administrator bootstrap on every startup: ensure this account exists with the admin role |
| `VIC_ADMIN_PASSWORD` | _(unset)_ | Password for the bootstrap account; required to create a missing admin, optional when promoting an existing user. Reapplies on each start — unset it afterwards if you do not want the password re-pinned |

## Test

```bash
uv run pytest -q
```

Baseline before multi-deck changes (2026-11-27): **65 passed**, 1 Starlette/httpx deprecation warning.
Current suite after card-formatting changes (#7): **90 passed**, 1 Starlette/httpx deprecation warning.

## Project layout

```text
src/virtual_index_card/
  app.py          FastAPI routes, auth, admin approval queue + user management, API, and templates
  admin.py        ensure_admin() shared by the CLI and env bootstrap
  create_admin.py `python -m virtual_index_card.create_admin` CLI
  config.py       Environment-based settings
  db.py           SQLite connection, schema version 4, and v1 → v2 → v3 → v4 migrations
  domain.py       Card model, validation, username/password rules, Fisher–Yates shuffle
  formatting.py   Rich-text document allowlist validation, visible-length checks, and safe HTML rendering
  repository.py   User-scoped SQLite queries and account-request persistence
  security.py     Password hashing, temporary-password generation, token helpers
  templates/      Jinja pages
  static/         CSS flip interaction and JavaScript
tests/            Unit and integration tests
uv.lock           Locked dependency versions
```

## Deployment notes

See the [Raspberry Pi deployment runbook](docs/raspberry-pi-deployment.md) for cloning onto `/mnt/ssd/git/virtual-index-card`, running Gunicorn on loopback port **10001** under systemd, and putting Nginx/Certbot in front of it. The runbook has not been verified on a Pi: HTTPS/reverse-proxy validation (`BL-022`) and scheduled off-device SQLite backups with a restore drill (`BL-023`) remain open. Set `VIC_COOKIE_SECURE=true` only when the app is served over HTTPS.

## Documentation

- [`PLAN.md`](PLAN.md) — implementation record and remaining roadmap.
- Open and proposed follow-up work is tracked through GitHub Issues; see [`PLAN.md`](PLAN.md) for this assignment's status.
- [`docs/backlog-archive.md`](docs/backlog-archive.md) — completed work history.
- [`docs/architecture.md`](docs/architecture.md) — as-built architecture.
- [`docs/raspberry-pi-deployment.md`](docs/raspberry-pi-deployment.md) — Raspberry Pi operator runbook (not yet tested on a Pi).
- [`docs/technical-decisions.md`](docs/technical-decisions.md) — decisions and rationale.
- [`AGENTS.md`](AGENTS.md) — repository operating instructions.
