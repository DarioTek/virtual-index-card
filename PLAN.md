# Active plan: Administrator approval for new accounts

## Objective

Introduce an **Administrator role**. New accounts are no longer self-created: a visitor
submits an *account request*, and an administrator approves it. On approval the system
creates the account and the administrator is given the account name/password to hand to
the user, who can then log in.

## Assignment context

- Requested on 2026-11-27 on branch `arena/6184b8bf-virtual-index-card`.
- Replaces open self-registration (BL-021 access decision from 2026-11-24).
- Previous assignment (Raspberry Pi deployment runbook) was completed 2026-11-24; its
  notes remain in the progress log of this file's history and in `docs/`.

## Scope / assumptions

- **In scope:** schema migration to version 2 (`users.role`, `account_requests`), request
  form replacing open registration, admin requests page (approve / reject / reset
  password), one-time credential display to the admin, first-admin bootstrap via CLI and
  env vars, schema-migration path for existing v1 databases, tests, docs.
- **Assumptions (flagged for the user):**
  - Credentials are **generated (or admin-chosen) at approval time and shown once to the
    administrator**, who relays them out-of-band (e.g. in person or by their own mail
    client). The app has no mail delivery and none is being added.
  - The requester supplies a *desired username* plus optional free-text contact/note, but
    **not** a password.
  - Existing v1 databases migrate in place on first start; all existing users become
    role `user`. No administrator exists until one is bootstrapped via the CLI or
    `VIC_ADMIN_USERNAME`/`VIC_ADMIN_PASSWORD`.
  - Emailing credentials automatically is out of scope (`BL-024` covers mail-based
    recovery and remains deferred).
- **Out of scope:** auto-emailing credentials, request rate limiting, multi-deck work
  (`BL-001`), promoting/demoting admins from the web UI (CLI covers promotion),
  audit-log UI beyond the `decided_by`/`decided_at` columns.

## Approach

1. `db.py`: schema version 2; migrate v1 → v2 (`ALTER TABLE users ADD role ... DEFAULT
   'user'`, create `account_requests`); unsupported versions still fail loudly.
2. `security.py`: `generate_temporary_password()` — readable, unambiguous alphabet.
3. `repository.py`: `create_user(..., role=...)`, request helpers (create/list/get/mark
   decided atomically when still pending), user role/password update helpers.
4. `create_admin.py`: `python -m virtual_index_card.create_admin USERNAME [--password]`;
   creates an admin or promotes an existing user. Env bootstrap in `create_app`:
   `VIC_ADMIN_USERNAME` + `VIC_ADMIN_PASSWORD` ensure an admin exists (created, promoted,
   and password reset to the env value — documented).
5. `app.py`: `/register` becomes the request form; new admin-gated routes
   `GET /admin/requests`, `POST /admin/requests/{id}/approve`,
   `POST /admin/requests/{id}/reject`, `POST /admin/users/{id}/reset-password`.
   Approve/reset render a shown-once credentials page. Non-admins get 403; anonymous
   visitors are redirected to `/login` (pages) or 401 (POST).
6. Templates: rewrite `register.html`, add `register_done.html`, `admin_requests.html`,
   `admin_credentials.html`; admin-only "Admin" nav link in `base.html`; admin styles.
7. Tests: conftest `register()` now drives the request → admin-approve → login flow with
   an explicit password; new `tests/test_admin.py` covers approval, rejection, duplicate
   requests, role gating, shown-once credentials, reset, and the v1→v2 migration.
8. Docs: README, `docs/architecture.md`, `docs/technical-decisions.md`,
   `docs/raspberry-pi-deployment.md` (registration exposure note), PLAN.md.

## Tasks

| # | Task | Status |
|---|---|---|
| 1 | Schema v2 + migration in `db.py` with v1 upgrade test | Completed |
| 2 | Security helper + repository request/role/password functions | Completed |
| 3 | Admin bootstrap: CLI + env env vars in create_app | Completed |
| 4 | Routes: request form, admin pages, approve/reject/reset, credentials page | Completed |
| 5 | Templates + styles + nav | Completed |
| 6 | Tests updated and expanded (`pytest -q` green) | Completed |
| 7 | Docs (README, architecture, technical decisions, Pi runbook) + final verification | Completed |

## Acceptance criteria

- [x] `GET /` for an unauthenticated visitor redirects to `/login`; `/register` shows an
      account-request form and creates a **pending** request (no user row, no session).
- [x] A pending/rejected requester cannot log in.
- [x] Approving a request creates exactly one user with role `user`; the response page
      shows the account name and password once; the user can then log in.
- [x] Non-admin authenticated users get 403 from admin routes and see no Admin nav link;
      anonymous visitors are redirected/401.
- [x] Rejected requests cannot be approved afterwards (decision is atomic on `pending`).
- [x] Existing v1 databases open and migrate on startup; existing users become role
      `user`; unsupported versions fail without data loss.
- [x] First admin is bootstrapped via `python -m virtual_index_card.create_admin` or
      `VIC_ADMIN_USERNAME`/`VIC_ADMIN_PASSWORD`; promoted via re-run on an existing user.
- [x] `uv run pytest -q` passes (47 passed, 1 existing Starlette/httpx deprecation
      warning); README and architecture docs describe the new flow.

## Risks / rollback

- Schema migration touches a live database: migration is additive only (new column with
  default, new table); v1 code reading a v2 database would break, so rollback = restore
  the pre-change database backup. Tested against a synthetic v1 fixture.
- Shown-once credentials: if lost, the admin uses "Reset password" (new shown-once
  value). No plaintext password is stored anywhere (asserted by tests).

## Proposed issues (not created; user decides)

- Automatic email delivery of credentials once mail is configured (overlaps `BL-024`).
- Rate limiting / CAPTCHA on the public request form.
- Web UI to promote/demote administrators and an audit view of decisions.

## Progress log

- 2026-11-27: Implemented and verified on `arena/6184b8bf-virtual-index-card`.
  - `db.py`: `SCHEMA_VERSION = 2`; fresh installs and v1 databases converge on the same
    schema (additive migration: `users.role` + `account_requests`); statements run inside
    the transaction (no implicit `executescript` commit). Synthetic-v1 migration covered
    by `test_migration_from_schema_v1`; unsupported versions raise without touching data.
  - `security.py`: `generate_temporary_password()` (unambiguous alphabet, `xxxx-xxxx-xxxx`).
  - `repository.py`: `create_user(..., role=...)`, `set_user_role`, `set_user_password`,
    `count_admins`, `delete_user_sessions`, full account-request CRUD with atomic
    `decide_account_request` (only from `pending`).
  - `admin.py` + `create_admin.py`: first-admin bootstrap CLI (create or promote;
    generated password printed once) and shared `ensure_admin()` used by app startup.
  - `config.py` / `app.py`: optional `VIC_ADMIN_USERNAME`/`VIC_ADMIN_PASSWORD` bootstrap at
    startup (reapplies on each start — documented); `/register` is now the request form;
    `/register/received` confirmation; admin-gated `/admin/requests`, approve/reject, and
    reset-password routes; shown-once credentials page; Admin nav link for admins.
  - Verification: `uv sync --group dev` OK; `uv run pytest -q` → **47 passed**, 1 existing
    warning. Live `curl` smoke against uvicorn on :10001 confirmed request → admin queue →
    approve (password generated once) → user login → admin reset → old session invalidated
    and new password works. Demo preview running on port 10001 with a disposable demo
    admin (see README); `data/` is git-ignored.
  - Docs: README, `docs/architecture.md`, `docs/technical-decisions.md` (TD-009),
    `docs/raspberry-pi-deployment.md`, PLAN.md.
- Assumptions to confirm with the user: credentials are relayed out of band by the
  administrator (no mail delivery); the requester does not choose a password at request
  time; open self-registration is removed entirely.
