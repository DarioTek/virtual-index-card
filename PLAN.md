# Active plan: Administrator UI to manage all users (view, delete, reset password)

## Objective

Add an `/admin/users` page for the **administrator** role listing every account, with a
**Delete** and a **Reset password** action per user. Complements the request queue from
the previous assignment (completed 2026-11-27, commit `c92a0d0`).

## Scope / assumptions

- **In scope:** `list_users` repository query (with card counts), `delete_user`,
  admin-gated `GET /admin/users` and `POST /admin/users/{id}/delete`, shown-once password
  reset via the existing reset endpoint (extended to all non-admin users), template, nav
  link, tests, docs. Deleting a user cascades to their cards and sessions (existing FK);
  approval-audit rows keep their content with `created_user_id`/`decided_by` set to NULL.
- **Assumptions:** administrator accounts cannot be deleted from the web UI (and cannot be
  reset there either — that remains `create_admin`/env bootstrap). This also means an
  admin cannot delete themselves. Deletes are permanent (no soft-delete/undo); the button
  asks for browser confirmation, matching the app's existing delete-card pattern.
- **Out of scope:** editing roles from the UI (CLI only), bulk actions/search/pagination
  (deck scale is small), email notifications on deletion.

## Acceptance criteria

- [x] `/admin/users` lists all users (username, role, card count, created) for admins;
      non-admins get 403, anonymous visitors are redirected to `/login`.
- [x] Per-user **Reset password** works for any non-admin account (not only approved
      ones), shows the new password once, and invalidates existing sessions.
- [x] Per-user **Delete** removes the account, their cards and sessions; audit rows are
      retained with user references set to NULL; admins cannot be deleted (400).
- [x] CSRF form token required for both actions; 404 for unknown user ids.
- [x] `uv run pytest -q` passes (**55 passed**); README/architecture/TD updated.

## Tasks

| # | Task | Status |
|---|---|---|
| 1 | Repository: `list_users`, `delete_user` | Completed |
| 2 | Routes: `/admin/users` GET, delete POST | Completed |
| 3 | Template `admin_users.html`, nav links (Requests/Users), styles | Completed |
| 4 | Tests + docs (README, architecture, TD-010) + verification | Completed |

## Progress log

- 2026-11-27: Assignment started (follow-up to `c92a0d0`).

- 2026-11-27 (follow-up): Implemented `/admin/users` + delete; reset endpoint extended to
  all non-admin accounts. `uv run pytest -q` → **55 passed**, 1 existing warning. Live
  curl verified the page, role gating and nav. Note: the demo preview database appeared
  to reset between turns (the previously approved `Geny` account is gone; the file now
  contains only `admin` + a pending `demo-user` request) — disposable demo state was
  wiped and recreated clean. Non-ephemeral deployments must use a persistent path and the
  backup discipline in `docs/raspberry-pi-deployment.md`.
