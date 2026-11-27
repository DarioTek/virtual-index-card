# Active plan: Admin Profile page (update username, change password)

## Objective

Add an `/admin/profile` page, linked from the admin nav, where the administrator can
(1) update their username and (2) change their password. Every change is authorized with
the current password. Follow-up to `a310c63` (admin Users page).

## Scope / assumptions

- **In scope:** admin-gated `GET`/`POST /admin/profile`; username update with NOCASE
  uniqueness check (case-only change allowed); password change with
  validate + confirm; other sessions invalidated on password change (current session
  kept); a note when `VIC_ADMIN_PASSWORD` re-pins the password on restart; template, nav
  link, tests, docs.
- **Assumptions:** page is admin-only (per request); regular accounts keep the existing
  admin-reset path. Sessions survive username changes (they key on `user_id`). Audit
  history keeps working because joins read live usernames.
- **Out of scope:** self-service profile for regular users; email change; avatar; 2FA.

## Tasks

| # | Task | Status |
|---|---|---|
| 1 | Repository: `update_username`, `delete_user_sessions_except` | Completed |
| 2 | Routes + POST validation + PRG redirect with `?saved=` flag | Completed |
| 3 | Template `admin_profile.html`, nav link, styles | Completed |
| 4 | Tests + docs + verification | Completed |

## Acceptance criteria

- [x] `/admin/profile` is admin-only (anon → redirect to /login, non-admin → 403).
- [x] Username change (incl. case-only) works, is unique NOCASE, and keeps the session.
- [x] Password change requires current password + confirmation; old password fails after.
- [x] Other sessions are invalidated on password change; current session stays valid.
- [x] Wrong current password / mismatch / duplicate username show inline errors.
- [x] `uv run pytest -q` passes (**65 passed**); README/architecture/TD updated.

## Progress log

- 2026-11-27: Assignment started.

- 2026-11-27 (follow-up): Implemented `/admin/profile` (admin-only): username rename with
  NOCASE uniqueness (case-only allowed), current-password-gated password change with
  confirmation, other-session invalidation keeping the current session. Live curl verified
  the page and the `VIC_ADMIN_PASSWORD` re-pin warning. `uv run pytest -q` → **65 passed**.
