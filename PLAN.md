# Active plan: Add single-card Review mode

## Objective

Add a focused **Review mode** to the implemented app: one index card at a time, tap/activate to flip from front to back, and previous/next controls that cycle through the deck in its saved order. This is `BL-025`. The original hosted app with individual accounts and SQLite remains the delivered baseline.

## Current assignment: Review mode

- **In scope:** authenticated `GET /review` route, a single-card template, tap-to-flip using the existing flip interaction, previous/next navigation with wrap-around, position indicator, empty state, navigation links, tests, and docs.
- **Out of scope:** known/unknown tracking and study results (`BL-006`), editing cards inside Review mode, changing shuffle behavior.
- **Selected backlog item:** `BL-025` (In Progress).

### Acceptance criteria

- [x] An authenticated user sees exactly one card at `/review`.
- [x] Activating the card flips it to the back and activating it again returns to the front.
- [x] Previous/next cycles through every card in deck order and wraps around.
- [x] The current position is visible, and an empty deck has a clear empty state.
- [x] Review mode shows only the signed-in account's cards and requires authentication.
- [x] `uv run pytest -q` passes with new Review mode tests.

## Verified repository state at start

- Branch `arena/bd203bc7-virtual-index-card`, based on `d493534` (`baseline`).
- Only control files, planning docs, and `.gitignore` existed; no source, manifest, database, or tests.
- Python `3.11.2` and Git `2.39.5` were available. `uv` was initially absent; `uv 0.13.9` was installed and adopted as the project tool on 2026-11-24.

## Decisions applied

1. Hosted server-side web application with SQLite as the sole persistent store.
2. Individual accounts for access control (`BL-021`).
3. One deck per account, plain-text notes, durable shuffled order.
4. CSRF protection, hashed passwords/session tokens, and user-scoped queries.

## Tooling migration (2026-11-24)

At the user's request, pip was replaced by uv for all project setup and commands. Dev dependencies moved from `[project.optional-dependencies]` to `[dependency-groups]`, `uv.lock` was generated and committed, and README/docs now use `uv sync --group dev` plus `uv run`. Verified with `uv run pytest -q` (20 passed).

## Scope delivered

- `pyproject.toml`, package skeleton, uv-based install instructions, and committed `uv.lock`.
- SQLite schema version 1 with `users`, `sessions`, and `cards` tables.
- Account registration, login, logout, PBKDF2 hashing, server-side sessions, CSRF tokens.
- Card CRUD and shuffle API; server-rendered deck page with CSS flip and JavaScript interactions.
- 24 automated tests and a live `uvicorn` smoke test, including Review mode.
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
| 17 | Migrate tooling from pip to uv | Completed | `[dependency-groups]`, `uv.lock`, README and docs switched to `uv sync` / `uv run`. |
| 18 | Add single-card Review mode (`BL-025`) | Completed | `GET /review`, `review.html`, shared flip handler, navigation tests. |
| 11 | Domain and SQLite persistence | Completed | `config.py`, `db.py`, `domain.py`, `repository.py`. |
| 12 | Authentication and session layer | Completed | `security.py`, account routes, templates, CSRF. |
| 13 | Card API | Completed | CRUD + shuffle with auth and CSRF. |
| 14 | Web UI | Completed | Deck page, forms, flip CSS, JS interactions. |
| 15 | Tests and validation | Completed | 24 tests passed; live smoke test passed, including Review mode. |
| 16 | Documentation and backlog closure | Completed | Docs updated; `BL-021` archived. |

## Acceptance criteria

- [x] Registration, login, and logout work; passwords are hashed and no secret is in Git.
- [x] Unauthenticated visitors cannot view, create, edit, delete, or shuffle cards.
- [x] Each account sees only its own cards; cross-account IDs return 404.
- [x] Create, edit, delete, flip, and shuffle work; shuffle order persists after reload.
- [x] All durable state is in SQLite.
- [x] Writes enforce CSRF; note content is escaped.
- [x] `uv run pytest -q` passes (24 tests) and README commands were verified.
- [x] `BL-021` was moved to `docs/backlog-archive.md` after verification.

## Files created or changed

- Created: `pyproject.toml`, `src/virtual_index_card/` (app, config, db, domain, repository, security, templates, static), `tests/`, `docs/backlog-archive.md`.
- Modified: `PLAN.md`, `BACKLOG.md`, `README.md`, `docs/architecture.md`, `docs/technical-decisions.md`, `.gitignore`.

## Validation and results

- Initial install used pip and exposed a missing `python-multipart` dependency; it is now declared in `pyproject.toml`.
- `uv lock` — resolved 33 packages and created `uv.lock`; `uv sync --group dev` — created a fresh `.venv` and installed all dependencies.
- `uv run pytest -q` — **24 passed**, 1 Starlette/httpx deprecation warning (20 before Review mode). An initial shuffle-order assertion failed because the test matched `aria-label` text; the test was corrected to compare `data-card-id` order.
- Live server: `VIC_DATABASE_PATH=... uv run uvicorn virtual_index_card.app:app --host 0.0.0.0 --port 8000` — started successfully. `curl` smoke test confirmed health check, unauthenticated redirect, registration, deck rendering, CSRF rejection (403), card creation, shuffle, reload order, logout, and Review mode (`Card 1 of 2`, one card rendered, wrap-around links).
- `git diff --check` — passed with no whitespace errors.
- Not run: browser-based visual inspection of the CSS flip animation, HTTPS deployment, backup restore drill, CI. The flip handler is shared with the already-used deck page and was verified in generated markup, not in a real browser.

## Backlog changes

- `BL-021` moved from `In Progress` to `docs/backlog-archive.md` with completion date and validation reference.
- `BL-025` (Review mode) added as In Progress, then archived after verification; active backlog returns to 23 items.
- `BL-024` repurposed to password reset/email verification (now distinct from delivered accounts).
- Active backlog: 23 items — 12 Ready, 8 Proposed, 3 Deferred.

## Remaining limitations

The app is functional locally but not production-hardened: no HTTPS, no backup automation, no CI, no password recovery, and no multiple decks. A Starlette/httpx deprecation warning remains in the test client.

## Next recommended action

Select deployment work — `BL-022` (HTTPS/reverse proxy) and `BL-023` (SQLite backups) — before exposing the app publicly, or choose a feature backlog item such as `BL-001` (multiple decks) or `BL-015` (CI).
