# Technical decisions

Product decisions were confirmed by the user; implementation choices below were validated in code on 2026-11-24 unless noted. Status values: `Proposed`, `Accepted`, `Rejected`, `Superseded`.

## TD-001: Hosted server-side web application

- **Date:** 2026-11-24
- **Status:** Accepted
- **Context:** The user asked for SQLite as the database and chose a hosted web app over browser-only or local-server options.
- **Decision:** Serve the app from a server; persist durable state in server-side SQLite.
- **Alternatives considered:** Browser-only with `localStorage`; SQLite WASM; native desktop/mobile app.
- **Consequences:** Centralized data and backups, but hosting, TLS, access control, and backups are required.

## TD-002: SQLite as the sole persistent store

- **Date:** 2026-11-24
- **Status:** Accepted
- **Context:** The user explicitly requested SQLite for any data needing persistence.
- **Decision:** Store users, session hashes, cards, positions, and schema version in SQLite via `sqlite3`.
- **Alternatives considered:** Browser storage, hosted database service, JSON files.
- **Consequences:** No extra database service; file-level backups remain essential (`BL-023`).

## TD-003: Durable deck order with Fisher–Yates shuffle

- **Date:** 2026-11-24
- **Status:** Accepted
- **Context:** The user confirmed that shuffle must persist across reloads.
- **Decision:** Store an integer `position` per card; shuffle in a pure domain module with an injectable RNG; rewrite positions in one transaction.
- **Alternatives considered:** Random sort keys, repeated random draws, transient order.
- **Consequences:** Deterministic tests, no duplicate/lost cards, reload restores saved order.

## TD-004: One deck, plain-text notes

- **Date:** 2026-11-24
- **Status:** Accepted
- **Context:** The user accepted one deck and plain-text notes for the first release.
- **Decision:** No deck selector or formatting toolbar; validate non-empty text and render with Jinja auto-escaping.
- **Alternatives considered:** Multiple decks, Markdown/rich text.
- **Consequences:** Smaller scope and reduced XSS surface.

## TD-005: FastAPI, uv-style manifest, and pytest

- **Date:** 2026-11-24
- **Status:** Accepted
- **Context:** `.gitignore` anticipated Python tooling; Python 3.11 is available and the app needs server rendering, an API, and SQLite.
- **Decision:** Python 3.11+, FastAPI, Jinja2, `sqlite3`, `pyproject.toml`, pip/venv for this sandbox, and pytest with the Starlette test client.
- **Alternatives considered:** Node/Express with a SQLite driver; ORM-heavy framework.
- **Consequences:** Few runtime dependencies; `uv` is not installed here, so README uses `python3 -m venv` plus pip. `pytest -q` passes with 20 tests.

## TD-006: Layered boundaries

- **Date:** 2026-11-24
- **Status:** Accepted
- **Context:** CRUD, ordering, HTTP handling, and SQL can become entangled.
- **Decision:** Separate UI, HTTP, domain, and persistence modules; route handlers delegate ordering decisions to the domain layer.
- **Alternatives considered:** Single-module application; ORM models as domain objects.
- **Consequences:** Domain logic is testable without a web client; storage can be replaced later.

## TD-007: Individual accounts with server-side sessions

- **Date:** 2026-11-24
- **Status:** Accepted
- **Context:** The user chose individual accounts for the hosted app, resolving `BL-021`.
- **Decision:** PBKDF2 password hashes with per-user salts, random session tokens stored only as SHA-256 hashes in SQLite, HttpOnly cookies, logout deletion, and double-submit CSRF tokens.
- **Alternatives considered:** Single shared password; no authentication; third-party identity provider.
- **Consequences:** Account isolation is enforced in every query. Password reset/email verification remain deferred (`BL-024`).

## TD-008: Access control, TLS, and backups as release gates

- **Date:** 2026-11-24
- **Status:** Accepted as policy; HTTPS/backups not yet implemented
- **Context:** Hosting a notes app exposes it to the internet; SQLite stores everything in one file.
- **Decision:** Treat access control, HTTPS, and tested backups as prerequisites for public deployment.
- **Alternatives considered:** Ship first, harden later; private-network-only operation.
- **Consequences:** Access control is delivered; TLS (`BL-022`) and backups (`BL-023`) are still open, so public deployment is not yet approved.

## Superseded decisions

- Browser-only static app with `localStorage`.
- Local-only Python server framed without hosting/access-control requirements.
