# Backlog archive

Completed backlog items are retained here for traceability. IDs are never reused; an archived item is not an authorization to reopen work.

### BL-021: Decide and implement access control for the hosted app

- **Category:** Security
- **Priority:** High
- **Status:** Completed (archived)
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** A hosted application must control who can read and change cards. The user chose individual accounts: registration, login/logout, hashed passwords, server-side sessions, and per-user card scoping.
- **Expected outcome:** Only authorized visitors can reach the deck, and access can be revoked.
- **Acceptance criteria:**
  - [x] An access-control model is chosen and documented.
  - [x] Unauthenticated visitors cannot view, create, edit, delete, or shuffle cards.
  - [x] Credentials are hashed or handled by a trusted proxy; no secrets are stored in Git.
  - [x] Access can be revoked without changing application code.
- **Dependencies:** None; decision resolved by the user on 2026-11-24. Related to `BL-013` and `BL-024`.
- **Related files/components:** Auth module, session store, templates, documentation.
- **Notes:** Selected for implementation in `PLAN.md`; verified by automated and live smoke tests before archival.
- **Plan reference:** `PLAN.md` task 12 and acceptance criteria.
- **Completion date:** 2026-11-24
- **Validation / delivery reference:** `pytest -q` — 20 passed (1 Starlette/httpx deprecation warning); live smoke test via `uvicorn` confirmed registration, login/logout, CSRF enforcement, card CRUD, shuffle, and reload persistence. Delivered in `src/virtual_index_card/` and `tests/`.

### BL-025: Single-card Review mode

- **Category:** Feature
- **Priority:** High
- **Status:** Completed (archived)
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Add a focused Review mode that shows one index card at a time, lets the user tap the card to flip it, and cycles through the rest of the deck with previous/next controls.
- **Expected outcome:** A user can review the whole deck card-by-card without seeing the full deck grid, in the deck's saved order.
- **Acceptance criteria:**
  - [x] An authenticated user can open `/review` and sees exactly one card.
  - [x] Tapping or activating the card flips it to the back; activating it again returns to the front.
  - [x] Previous and next controls cycle through every card in order and wrap around at the ends.
  - [x] The card position (for example, "Card 2 of 5") is visible.
  - [x] An empty deck shows a helpful empty state.
  - [x] Users see only their own cards.
- **Dependencies:** None; uses the existing card repository and template layout.
- **Related files/components:** `app.py`, `templates/review.html`, `static/app.js`, `static/styles.css`, tests.
- **Notes:** Distinct from `BL-006`, which adds known/unknown tracking and session results.
- **Plan reference:** `PLAN.md` current assignment.
- **Completion date:** 2026-11-24
- **Validation / delivery reference:** `uv run pytest -q` — 24 passed (20 before Review mode, 4 new Review tests); live `curl` smoke test confirmed single-card rendering, position indicator, flip control markup, next/wrap links. Delivered in `app.py`, `templates/review.html`, `static/app.js`, `static/styles.css`.
