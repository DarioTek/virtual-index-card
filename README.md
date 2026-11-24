# virtual-index-card

A hosted web application for personal index cards. Each registered account has one private deck: write notes on a card's front and back, flip between them, add/edit/delete cards, and shuffle the deck. The shuffled order persists across reloads.

All durable data — accounts, sessions, cards, and card order — is stored in **SQLite**.

## Features

- Individual accounts with registration, login, and logout.
- Per-account decks: one user cannot see or modify another user's cards.
- Add, edit, delete, flip, and shuffle cards.
- Plain-text notes with safe HTML escaping.
- CSRF-protected writes and hashed passwords/session tokens.

## Prerequisites

- Python 3.11 or newer with `venv` and `pip`.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Run locally

```bash
VIC_DATABASE_PATH=./data/virtual-index-card.sqlite3 \
  .venv/bin/uvicorn virtual_index_card.app:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000> and create an account. The SQLite file is created automatically on first start and is ignored by Git.

Configuration (all optional):

| Variable | Default | Purpose |
|---|---|---|
| `VIC_DATABASE_PATH` | `data/virtual-index-card.sqlite3` | Location of the SQLite database |
| `VIC_SESSION_TTL_SECONDS` | `604800` | Session lifetime in seconds |
| `VIC_COOKIE_SECURE` | `false` | Set to `true` when serving over HTTPS |

## Test

```bash
.venv/bin/pytest -q
```

Verified on 2026-11-24: **20 passed**, 1 Starlette/httpx deprecation warning.

## Project layout

```text
src/virtual_index_card/
  app.py          FastAPI routes, auth, API, and templates
  config.py       Environment-based settings
  db.py           SQLite connection and schema version 1
  domain.py       Card model, validation, Fisher–Yates shuffle
  repository.py   User-scoped SQLite queries
  security.py     Password hashing and token helpers
  templates/      Jinja pages
  static/         CSS flip interaction and JavaScript
tests/            Unit and integration tests
```

## Deployment notes

This release is not yet hardened for public hosting. HTTPS/reverse-proxy configuration (`BL-022`) and scheduled SQLite backups (`BL-023`) remain open. Set `VIC_COOKIE_SECURE=true` only when the app is served over HTTPS.

## Documentation

- [`PLAN.md`](PLAN.md) — implementation record and remaining roadmap.
- [`BACKLOG.md`](BACKLOG.md) — active future work.
- [`docs/backlog-archive.md`](docs/backlog-archive.md) — completed work history.
- [`docs/architecture.md`](docs/architecture.md) — as-built architecture.
- [`docs/technical-decisions.md`](docs/technical-decisions.md) — decisions and rationale.
- [`AGENTS.md`](AGENTS.md) — repository operating instructions.
