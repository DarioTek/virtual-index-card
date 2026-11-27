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
- **Consequences:** Deterministic tests, no duplicate/lost cards, reload restores saved Review order. The management page separately sorts by creation time (`created_at DESC, id DESC`), so shuffling Review never rearranges card-management display. The shuffle control is available only in Review and resets the cursor to card 1.

## TD-004: One deck, plain-text notes

- **Date:** 2026-11-24
- **Status:** Accepted
- **Context:** The user accepted one deck and plain-text notes for the first release.
- **Decision:** No deck selector or formatting toolbar; validate non-empty text and render with Jinja auto-escaping.
- **Alternatives considered:** Multiple decks, Markdown/rich text.
- **Consequences:** Smaller scope and reduced XSS surface.

## TD-005: FastAPI with uv and pytest

- **Date:** 2026-11-24
- **Status:** Accepted
- **Context:** `.gitignore` anticipated Python tooling; Python 3.11 is available and the app needs server rendering, an API, and SQLite.
- **Decision:** Python 3.11+, FastAPI, Jinja2, `sqlite3`, `pyproject.toml` with `[dependency-groups]`, uv for environment/lockfile management, and pytest with the Starlette test client.
- **Alternatives considered:** Node/Express with a SQLite driver; ORM-heavy framework.
- **Consequences:** Few runtime dependencies and reproducible installs from committed `uv.lock`. `uv sync --group dev` and `uv run pytest -q` were verified with 20 passing tests.

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

## TD-009: Administrator-approved accounts with shown-once credentials

- **Date:** 2026-11-27
- **Status:** Accepted
- **Context:** Open self-registration had to be closed: the app creates one private deck per account and is intended for a small, controlled audience. The user asked for an administrator role who approves account-creation requests, after which the user receives an account name/password to log in.
- **Decision:** Replace open registration with an account-request queue. Visitors file a request (desired account name, optional contact/note); administrators (`users.role = 'admin'`) approve or reject at `/admin/requests`. Approval creates the account with the requested or an edited account name and an admin-chosen or generated temporary password (unambiguous alphabet) that is displayed **once** to the administrator, who relays it out of band. Decisions are atomic (`UPDATE ... WHERE status = 'pending'`). Administrators can also reset a generated account's password, which signs the user out everywhere. Schema v2 migrates v1 in place (additive only); existing accounts become `user`. The first administrator is bootstrapped out of band: `python -m virtual_index_card.create_admin` or `VIC_ADMIN_USERNAME`/`VIC_ADMIN_PASSWORD` at startup.
- **Alternatives considered:** Requester chooses a password at request time (activation-on-approval); automatic email delivery of credentials; invite tokens generated by admins; per-request plaintext password storage to allow re-display.
- **Consequences:** Account creation is centrally controlled and auditable (`decided_by`, `decided_at`, `created_user_id`). Credentials travel out of band, so their delivery depends on the administrator's contact channel and mail hygiene (no automated delivery until mail is configured; `BL-024`). Lost credentials require a reset from the queue or `create_admin`. Passwords are never stored or re-displayed; a reset is the only recovery path. One-time display means an administrator who refreshes the result page loses the value — the page states this explicitly.

## TD-010: Administrator user management with protected admin accounts

- **Date:** 2026-11-27
- **Status:** Accepted
- **Context:** After adding the request queue, administrators still had no way to see all existing accounts or remove/reset non-admin ones (e.g. revoking access when someone leaves).
- **Decision:** Add `/admin/users` listing every account (username, role badge, card count, created date) with per-row actions. **Delete** is permanent and limited to non-admin accounts — it cascades to cards and sessions via existing foreign keys, and approval-audit rows are kept with `created_user_id`/`decided_by` set to NULL. **Reset password** reuses the shown-once generation endpoint for any non-admin account, not only approved ones. Administrator accounts are protected from both actions in the web UI (reset via `create_admin --password`, removal by role change out of band), so the last admin cannot lock the web UI. Deletes ask for browser confirmation, matching the existing delete-card pattern.
- **Alternatives considered:** Soft-delete/undo; deleting admin accounts from the UI with a last-admin guard; full-text search/pagination (deferred — the audience is small).
- **Consequences:** Revocation no longer requires shell access. Destructive deletes are one click past a browser confirm; backups (`BL-023`) remain the recovery path. No schema change was needed.

## Superseded decisions

- Browser-only static app with `localStorage`.
- Local-only Python server framed without hosting/access-control requirements.
