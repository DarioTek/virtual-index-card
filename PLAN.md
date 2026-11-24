# Active plan: Implement hosted index-card app with individual accounts — completed locally

## Objective

Implement the first release of `virtual-index-card`: a hosted FastAPI web application where registered users manage one private deck of plain-text index cards, flip cards front/back, add/edit/delete cards, and shuffle the deck. All durable data is stored in SQLite. This objective has been met locally; deployment hardening remains backlog work.

## Verified repository state at start

- Branch `arena/bd203bc7-virtual-index-card`, based on `d493534` (`baseline`).
- Only control files, planning docs, and `.gitignore` existed; no source, manifest, database, or tests.
- Python `3.11.2`, pip `23.0.1`, and Git `2.39.5` were available; `uv` was not installed.

## Decisions applied

1. Hosted server-side web application with SQLite as the sole persistent store.
2. Individual accounts for access control (`BL-021`).
3. One deck per account, plain-text notes, durable shuffled order.
4. CSRF protection, hashed passwords/session tokens, and user-scoped queries.

## Scope delivered

- `pyproject.toml`, package skeleton, and pip/venv install instructions.
- SQLite schema version 1 with `users`, `sessions`, and `cards` tables.
- Account registration, login, logout, PBKDF2 hashing, server-side sessions, CSRF tokens.
- Card CRUD and shuffle API; server-rendered deck page with CSS flip and JavaScript interactions.
- 20 automated tests and a live `uvicorn` smoke test.
- Updated README, as-built architecture, decision record, and backlog archive.

Out of scope and still open: HTTPS/reverse proxy (`BL-022`), scheduled backups (`BL-023`), CI (`BL-015`), multiple decks (`BL-001`), rich text (`BL-004`), password reset (`BL-024`), and hosting-target research (`BL-020`).

## Architecture delivered

```
Browser → FastAPI app → domain (Card, shuffle) → sqlite3 repository → SQLite file
```

- Notes are escaped by Jinja; flips are CSS/JS only.
- All card queries filter by `user_id`.
- Shuffle rewrites positions in one transaction and survives reload.
- Sessions are random tokens in HttpOnly cookies; only SHA-256 hashes are stored.

## Task status

| # | Task | Status | Result |
|---|---|---|---|
| 1–9 | Inspection, planning, and decision rounds | Completed | Control files and docs updated. |
| 10 | Tooling bootstrap | Completed | `pyproject.toml`, `.venv`, `src/`, `tests/`; dependencies installed. |
| 11 | Domain and SQLite persistence | Completed | `config.py`, `db.py`, `domain.py`, `repository.py`. |
| 12 | Authentication and session layer | Completed | `security.py`, account routes, templates, CSRF. |
| 13 | Card API | Completed | CRUD + shuffle with auth and CSRF. |
| 14 | Web UI | Completed | Deck page, forms, flip CSS, JS interactions. |
| 15 | Tests and validation | Completed | 20 tests passed; live smoke test passed. |
| 16 | Documentation and backlog closure | Completed | Docs updated; `BL-021` archived. |

## Acceptance criteria

- [x] Registration, login, and logout work; passwords are hashed and no secret is in Git.
- [x] Unauthenticated visitors cannot view, create, edit, delete, or shuffle cards.
- [x] Each account sees only its own cards; cross-account IDs return 404.
- [x] Create, edit, delete, flip, and shuffle work; shuffle order persists after reload.
- [x] All durable state is in SQLite.
- [x] Writes enforce CSRF; note content is escaped.
- [x] `pytest -q` passes and README commands were verified.
- [x] `BL-021` was moved to `docs/backlog-archive.md` after verification.

## Files created or changed

- Created: `pyproject.toml`, `src/virtual_index_card/` (app, config, db, domain, repository, security, templates, static), `tests/`, `docs/backlog-archive.md`.
- Modified: `PLAN.md`, `BACKLOG.md`, `README.md`, `docs/architecture.md`, `docs/technical-decisions.md`, `.gitignore`.

## Validation and results

- `.venv/bin/python -m pip install -e '.[dev]'` — succeeded; added `python-multipart` after FastAPI reported it required for form parsing.
- `.venv/bin/pytest -q` — **20 passed**, 1 Starlette/httpx deprecation warning. An initial shuffle-order assertion failed because the test matched `aria-label` text; the test was corrected to compare `data-card-id` order.
- Live server: `VIC_DATABASE_PATH=... .venv/bin/uvicorn virtual_index_card.app:app --host 0.0.0.0 --port 8000` — started successfully. `curl` smoke test confirmed health check, unauthenticated redirect, registration, deck rendering, CSRF rejection (403), card creation, shuffle, reload order, and logout.
- `git diff --check` — passed with no whitespace errors.
- Not run: browser-based visual inspection, HTTPS deployment, backup restore drill, CI.

## Backlog changes

- `BL-021` moved from `In Progress` to `docs/backlog-archive.md` with completion date and validation reference.
- `BL-024` repurposed to password reset/email verification (now distinct from delivered accounts).
- Active backlog: 23 items — 12 Ready, 8 Proposed, 3 Deferred.

## Remaining limitations

The app is functional locally but not production-hardened: no HTTPS, no backup automation, no CI, no password recovery, and no multiple decks. A Starlette/httpx deprecation warning remains in the test client.

## Next recommended action

Select deployment work — `BL-022` (HTTPS/reverse proxy) and `BL-023` (SQLite backups) — before exposing the app publicly, or choose a feature backlog item such as `BL-001` (multiple decks) or `BL-015` (CI).
