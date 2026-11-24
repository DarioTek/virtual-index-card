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
