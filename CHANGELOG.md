# Changelog

All notable changes to this project are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Backlog items that are not yet released are tracked as GitHub Issues, not in this file.

## [Unreleased]

### Added

- Public read-only deck links (#4): owners create, rotate, and revoke an unlisted link that renders one deck for anonymous visitors. Tokens are bearer secrets stored only as SHA-256 hashes and displayed once with a locally generated QR code; shared responses are `no-store`, `noindex`, and `no-referrer`.
- Versioned, full-fidelity JSON export of a single owned deck at `/decks/{id}/export.json`, with configurable `VIC_MAX_EXPORT_ROWS` and `VIC_MAX_EXPORT_BYTES` limits (HTTP 413 when exceeded).
- `.env` file support via `python-dotenv`: `load_settings()` reads a `.env` in the working directory, and real environment variables take precedence. See `.env.example`.
- `docs/operations.md` documenting the start/stop scripts, PID and log files, and how they differ from the systemd unit.

### Changed

- Schema v5 adds the `deck_shares` table; existing v1–v4 databases migrate in place.
- Invalid non-numeric or non-positive values for `VIC_SESSION_TTL_SECONDS`, `VIC_MAX_EXPORT_ROWS`, or `VIC_MAX_EXPORT_BYTES` now fail at startup with a clear `ValueError` instead of a bare `int()` traceback.

### Documentation

- Repository-wide documentation audit: removed obsolete backlog/prompt/git-command files, replaced dead `BL-*` identifiers with GitHub Issues, corrected the deployment runbook's branch instructions to `main`, and reconciled counts, paths, and endpoints with the code.

## [0.2.0] - 2026-11-27

### Added

- Administrator-approved accounts: visitors request an account, an administrator approves or rejects it, and the new credentials are shown once for out-of-band delivery.
- Administrator user management at `/admin/users`: list every account with role and card count, permanently delete non-admin accounts, and reset non-admin passwords (which signs the user out everywhere).
- Administrator profile at `/admin/profile`: change the administrator's own username and password; a password change invalidates other sessions but keeps the current one.
- First-administrator bootstrap via `python -m virtual_index_card.create_admin` or the `VIC_ADMIN_USERNAME` / `VIC_ADMIN_PASSWORD` environment variables.
- Multiple private decks per account, with generated sequential names (`My Deck 1`, `My Deck 2`, …), optional custom names, and renaming (schema v3).
- Deck deletion for empty, non-last decks, protected by a single conditional delete.
- Rich-text card formatting (schema v4, issue #7): bold, italic, underline, and a fixed WCAG AA 4-color palette (black, green, red, blue) on both card faces, with overlapping styles, a 5,000 visible Unicode code-point limit per side, canonical server-side validation, and verbatim preservation of existing plain-text cards.
- Background start/stop scripts (`virtual-index-card-start.sh`, `virtual-index-card-stop.sh`) and `docs/operations.md`.
- `docs/architecture.md`, `docs/technical-decisions.md` (TD-001 … TD-015), and the Raspberry Pi deployment runbook.

### Changed

- Registration is no longer open: accounts are created only by administrator approval.
- Gunicorn runs on loopback `127.0.0.1:10001` with the `uvicorn-worker` worker class; the application is expected behind a reverse proxy.
- The interactive API docs and OpenAPI schema are disabled by default and enabled only with `VIC_ENABLE_DOCS=true`.

### Fixed

- `virtual_index_card.__version__` now matches the packaged version.

### Removed

- Block-quote formatting and the orange/pink palette options from issue #7's original scope, at the user's request. Records that already contain block quotes still render safely.

## [0.1.0] - 2026-11-24

### Added

- Hosted FastAPI index-card application backed by SQLite.
- Individual accounts with login/logout, PBKDF2 password hashes, server-side session tokens, and double-submit CSRF protection.
- Card create, edit, delete, and flip, with the management page listing newest-created cards first.
- Single-card Review mode with previous/next navigation and wrap-around.
- Durable Review shuffle via Fisher–Yates, persisted per deck across reloads, with the shuffle control available only in Review.
- Unit and integration test suite covering domain, repository, security, and HTTP flows.
