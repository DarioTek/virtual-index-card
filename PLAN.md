# Active plan: Review-only shuffle control and newest-first card management

## Objective and scope

The card-management page should show the latest-created card first and the oldest last. The shuffle control should be available in Review mode, not on the card-management page. The user's earlier requirement that shuffle order survive reloads still applies: Review uses persisted `position`, while management uses creation order independently. This is a refinement of archived `BL-025`; tracked here as `BL-026`.

## Assumptions and risks

- “During the review session” means the shuffle action is exposed on the Review page, not that the saved order expires when the user leaves Review. No separate ephemeral session/order store is introduced.
- `created_at` has second-level precision, so `id DESC` breaks timestamp ties to reliably show later inserts first. Edits must not reorder cards.
- The existing authenticated CSRF-protected shuffle API remains the backing action; the UI starts at the first card of the new order after a shuffle. No database migration is required.

## Tasks

| # | Task | Status |
|---|---|---|
| 1 | Split repository reads into newest-first management and saved-order review; update routes | Completed |
| 2 | Move shuffle button to Review and make it restart at the first shuffled card | Completed |
| 3 | Add regression tests for page controls, ordering after create/edit/shuffle/reload, Review order and isolation | Completed |
| 4 | Update user/architecture docs, run full validation and review diff; archive `BL-026` only after verification | Completed |

## Acceptance criteria

- [x] The management page has no shuffle button, and newly created cards render first even after shuffle/reload; edits do not reorder cards.
- [x] Review offers a shuffle button for a nonempty deck, shows one card at a time, and shuffle restarts Review at card 1 in the saved new order (source-inspected navigation; not browser-tested).
- [x] A fresh login/reload preserves Review's shuffled order without changing the management page's newest-first sort.
- [x] Authentication, CSRF and per-account isolation remain intact; the full pytest suite and `git diff --check` pass.

## Validation strategy

Use repository and FastAPI integration tests (`uv run pytest -q`), check generated markup and saved order after login with an independent client, and inspect `git diff --check` plus final status. JavaScript navigation is inspected statically; browser-based visual interaction is not part of this assignment.

## Progress log

- 2026-11-24: Read `AGENTS.md`, the old plan/backlog, architecture/decision docs, routes, repository, templates, JS and existing tests; working tree clean on `arena/bd203bc7-virtual-index-card`. Established the two independent ordering rules and started task 1.
- Split reads in `repository.py`: management sorts `created_at DESC, id DESC`, Review retains persisted `position` order; `app.py` now chooses the right query per page. No schema changes.
- Moved the shuffle button from `deck.html` to `review.html`, disabled for one card and omitted for none. `app.js` posts the existing authenticated/CSRF-protected shuffle action then navigates to `/review` (card 1); `styles.css` handles disabled and wrapping controls.
- Updated `tests/test_app.py` and `tests/test_repository.py` for ordering, edit/shuffle independence, fresh-login Review order, button visibility and CSRF; updated `README.md`, `docs/architecture.md` and `docs/technical-decisions.md`. `uv run pytest -q`: 25 passed, 1 known Starlette/httpx deprecation warning. `node --check src/virtual_index_card/static/app.js` and `git diff --check`: passed. Browser visual/interaction check not run; JS navigation verified by source inspection.
- Archived `BL-026` after validation in `docs/backlog-archive.md`; restored active backlog counts to 23 (8 Proposed, 12 Ready, 3 Deferred). No commit or push requested. Next: obtain user feedback or tackle a selected backlog item.
