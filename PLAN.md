# Active plan: Revocable public read-only deck links (#4) — implemented

## Objective

Implement [GitHub Issue #4](https://github.com/DarioTek/virtual-index-card/issues/4): let a deck owner generate an unlisted, unguessable, revocable public link that shows one deck's cards read-only to visitors without an account — without granting mutation, exposing owner data, or weakening the existing session/CSRF boundaries.

**Status:** Implemented and validated on 2026-11-28. Issue #4 remains open until the acceptance criteria below are confirmed and the user authorizes closing it. See "Implementation notes" for where the delivery differs from the original design.

## Confirmed scope and proposed design decisions

### In scope (#4)
- Owner-only controls to **create**, **copy**, and **revoke/rotate** a public link for a deck they own.
- An anonymous route that renders a shared deck: card fronts/backs, flip interaction, and navigation through the deck's saved Review order.
- Unguessable tokens generated from a cryptographically secure source, compared safely, and stored hashed where feasible.
- Safe failure for revoked, rotated, deleted-deck, and unknown tokens — identical responses that do not reveal whether a deck exists.
- No owner details, private deck lists, admin navigation, session data, or CSRF tokens in shared responses.
- Additive SQLite schema migration and full account/deck isolation preserved.
- Documentation updates: `README.md`, `docs/architecture.md`, `docs/technical-decisions.md`, `CHANGELOG.md`, and `PLAN.md`.

### Out of scope (from #4)
- Public edit access, named-account sharing, viewer/editor roles.
- Searchable or enumerable public deck directories; usage analytics.
- Automatic or mandatory expiration.
- Public export/import, and public shuffle that changes saved Review order.
- Rate limiting (not included unless a separate security issue requires it).
- Implementing #5 (JSON import/export).

### Proposed resolutions for #4 open questions (pending approval)
1. **Storage and schema v5:** add `deck_shares(id, deck_id, user_id, token_hash, token_hint, created_at, revoked_at)` with `FOREIGN KEY (deck_id, user_id) REFERENCES decks(id, user_id) ON DELETE CASCADE` plus `FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE`, matching `TD-014`'s consequence that an eligible deck deletion must revoke access. One active share per deck enforced by a partial unique index on `(deck_id) WHERE revoked_at IS NULL`. Store only `sha256(token)`; keep a short non-secret `token_hint` (for example the first 8 characters) so the owner can tell links apart in the UI.
   - *Alternative:* a nullable `decks.share_token_hash` column. Rejected because rotation history and revocation auditing need rows, and #4 asks for rotation as a first-class action.
2. **Token format and comparison:** use the existing `security.new_token()` (`secrets.token_urlsafe(32)`, 256 bits), hash with `security.hash_token()`, and compare with `hmac.compare_digest` via `tokens_match()`. No new crypto primitive.
3. **Routing:** `GET /s/{token}` renders the shared deck read-only; `POST /decks/{deck_id}/share`, `POST /decks/{deck_id}/share/rotate`, and `POST /decks/{deck_id}/share/revoke` are owner-only, CSRF-protected form posts consistent with the existing deck forms. The public route must never appear in the authenticated nav.
4. **Shared-view navigation:** use a `?index=` cursor over the deck's persisted `position` order, mirroring `/review` but with no mutation controls. Review order is displayed as saved; there is no shuffle.
5. **Caching and indexing:** send `Cache-Control: no-store` and `X-Robots-Tag: noindex, nofollow` on shared responses so revoked content is not retained by shared caches. Add `<meta name="robots" content="noindex">` to the shared template.
6. **Presentation of card content:** reuse the existing `card_faces` macro and `render_card_face()` so formatted cards render identically, and plain-text cards stay escaped. No new renderer.
7. **Front-end surface:** the shared page loads its own minimal script (or the existing `app.js` guarded so no authenticated fetch runs). No CSRF meta tag is emitted, because the page has no writes.

## Delivery order and tasks

| # | Task | Related issue | Likely components | Status |
|---|---|---|---|---|
| 1 | Approve schema, token, routing, caching, and revocation decisions | #4 | `PLAN.md`, `docs/technical-decisions.md` | Completed |
| 2 | Add schema v5 (`deck_shares` + indexes) and the `v4 -> v5` additive migration | #4 | `src/virtual_index_card/db.py` | Completed |
| 3 | Add repository functions: create/get/rotate/revoke share, resolve token owner, list shares for a deck; all deck-scoped | #4 | `src/virtual_index_card/repository.py` | Completed |
| 4 | Add owner-only share routes and the anonymous `GET /s/{token}` route with safe 404s | #4 | `src/virtual_index_card/app.py` | Completed |
| 5 | Build the share controls on the deck page and the read-only shared template | #4 | `src/virtual_index_card/templates/deck.html`, new `shared_deck.html`, `src/virtual_index_card/static/` | Completed |
| 6 | Tests: anonymous access, token entropy/uniqueness, revocation, rotation, deleted decks, invalid tokens, mutation rejection, CSRF boundaries, data leakage, multi-deck isolation | #4 | `tests/test_app.py`, `tests/test_repository.py`, `tests/test_domain.py` | Completed |
| 7 | Run the full validation set and update `README.md`, `docs/architecture.md`, `docs/technical-decisions.md` (new TD-016), `CHANGELOG.md` | #4 | docs, root Markdown | Completed |

## Acceptance criteria

- [x] An owner can generate a public link for a deck they own; other owners cannot.
- [x] The link works without authentication and shows only that deck's cards.
- [x] Anonymous viewers can flip and navigate cards without persisting any change.
- [x] Every mutation attempt through public access is rejected (no write routes are exposed).
- [x] Revocation invalidates the existing link immediately; rotation invalidates the old token and issues a different one.
- [x] Invalid, revoked, and deleted-deck tokens return the same response and do not reveal whether a deck exists.
- [x] Deleting an eligible empty shared deck removes or invalidates its link via foreign-key cascade.
- [x] Shared pages expose no owner username, deck list, admin navigation, session cookie, or CSRF token.
- [x] Shared responses are `no-store` and marked `noindex, nofollow`.
- [x] Formatted and plain-text cards render exactly as in Management and Review.
- [x] Security-focused unit and integration tests pass, and the documented commands in the touched docs were re-run or marked unverified.

## Validation strategy

1. **Schema and migration tests:** fresh v5 creation; `v1/v2/v3/v4 -> v5` preserving all cards, rich payloads, and Review positions; `PRAGMA foreign_key_check`; partial unique index prevents two active shares per deck.
2. **Repository tests:** create/resolve/rotate/revoke, hashed tokens only, cross-account and cross-deck returns `None`, cascade on deck delete.
3. **HTTP and security tests:** anonymous `GET /s/{token}` success and safe 404s, no `vic_session`/`vic_csrf` required, no leakage of the owner's username or deck list, all mutation endpoints still 401/403/404 for anonymous callers, CSRF still required for the owner's share actions, token entropy sanity.
4. **Template checks:** shared page contains no admin nav, no CSRF meta tag, `noindex` present, formatted and plain text escape correctly.
5. **Manual/live check:** `uvicorn` smoke test of the full share → view → rotate → revoke cycle; documented in the progress log.

## Dependencies and risks

- **Expanded unauthenticated attack surface:** the public route is reachable without a session. Mitigation: token-only lookup with hashed storage, constant-time comparison, no write paths, uniform 404s, and explicit no-store/noindex headers.
- **Leakage through the shared template:** reusing `base.html` risks pulling in authenticated navigation. Mitigation: a dedicated minimal template that does not extend the authenticated chrome, covered by a template test asserting the absence of admin/user markup.
- **Deck deletion and shares:** `TD-014` requires share rows to cascade on deck delete. Mitigation: composite foreign key in schema v5 plus a migration test.
- **Depends on:** #1 (deck ownership) — delivered. Interacts with #5 (import/export must not carry sharing tokens) — not yet implemented.
- **Rollback:** the migration is additive; a rollback is dropping the new table. No existing column changes.

## Progress log

- 2026-11-28: Repository-wide documentation audit completed (no code changes other than the approved fixes below). Established that the repository's local history begins at commit `1d13507` ("Add virtual-index-card-stop.sh"), so there is no pre-audit branch/commit trail to reconcile beyond that point.
- 2026-11-28: Applied the user-approved fixes from the audit: version alignment to `0.2.0`, API docs routes gated behind `VIC_ENABLE_DOCS`, start/stop scripts corrected (loopback bind + `uvicorn_worker`), obsolete docs removed, and all remaining docs reconciled with the code.
- 2026-11-28: Opened this plan for Issue #4 at the user's direction. Awaiting approval before implementation.

## Next Recommended Action (superseded)

Present the implementation plan for Issue #4 (in particular the schema-v5 decision in item 1) and wait for approval. On approval, start with Task 1, then Tasks 2–3 (schema and repository) before any route work.

## Implementation notes

Deviations from the proposed design, and why:

1. **No `token_hint` column.** The proposal suggested storing a short non-secret prefix so the owner could tell links apart. The delivered UI shows the creation date and the rotate/revoke actions instead, so no part of the token is stored in readable form. Fewer secret-adjacent bytes at rest.
2. **`GET /s/{token}` only.** The proposed extra `/s/{token}/card/{index}` route was dropped; `?index=` matches the existing `/review` pattern and keeps one public path.
3. **No `/s/{token}/shuffle`.** A "405 only" endpoint was prototyped and removed: it added an unauthenticated route that could only ever fail.
4. **Standalone template.** `shared_deck.html` and `shared_missing.html` do not extend `base.html`, so no authenticated navigation, CSRF meta tag, or user chip can leak in. Covered by an explicit test.
5. **`python-dotenv` folded in, as directed.** `load_settings()` now reads `.env` (real environment variables win) and validates integer settings. This closes proposed issue 5 from the audit.
6. **One-way export shipped early.** `/decks/{id}/export.json` landed with this work because the configurable limits (#5) needed a home; import remains Issue #5.

Validation performed: `uv run pytest -q` (full suite green, one pre-existing Starlette/httpx warning), `python -m compileall -q src tests`, `node --check` on `app.js` and `shared.js`, `git diff --check`, plus a live `TestClient` walkthrough of create → anonymous view → navigate → rotate → revoke → export.

## Progress log

- 2026-11-28: Implemented schema v5 (`deck_shares` + migration), share repository functions, owner share routes, the anonymous `/s/{token}` route, the standalone shared templates and `shared.js`, the deck-page share panel, and the JSON export route with configurable limits.
- 2026-11-28: Added `python-dotenv` as a runtime dependency with `.env` loading and integer validation in `config.py`.
- 2026-11-28: Added `tests/test_config.py` and sharing/export coverage in `tests/test_app.py`; updated migration tests to schema v5 and added a v4 → v5 case.
- 2026-11-28: Updated `README.md`, `docs/architecture.md`, `docs/technical-decisions.md` (TD-016), `docs/operations.md`, `.env.example`, and `CHANGELOG.md`.

## Next Recommended Action

Review the shared-deck implementation and the Issue #4 acceptance criteria. On your confirmation: close #4 with a summary comment, then open the plan for #5 (JSON import), which now only needs the import half plus collision handling.

## Proposed Issues

Drafted from the documentation audit; **not filed**. Each needs user approval before creation.

1. **Add CI for the standard validation set** — labels `enhancement`, `priority: medium`. Run `uv sync --group dev`, `uv run pytest -q`, `uv run python -m compileall -q src tests`, `node --check src/virtual_index_card/static/app.js`, and `git diff --check` on every pull request. Acceptance: a workflow fails on any of those checks; `docs/architecture.md` "no CI yet" limitation is removed.
2. **Check documentation links and anchors in CI** — labels `documentation`, `priority: low`. Acceptance: a script fails the build on a broken internal link/anchor or a reference to a nonexistent branch/issue.
3. **Assert documentation claims from code** — labels `documentation`, `testing`, `priority: low`. A `tests/test_docs.py` that checks every documented `VIC_*` variable exists in `config.py`, the documented palette equals `PALETTE_COLORS`, and the endpoint table matches the registered routes.
4. **Generate `docs/api.md` from the OpenAPI schema** — labels `documentation`, `priority: low`. Documented request/response shapes for `/api/cards*` and `/api/deck/shuffle`, generated with `VIC_ENABLE_DOCS=true` rather than hand-written.
5. ~~**Add `.env`-based local configuration**~~ — **delivered with #4** (`python-dotenv`, `load_settings()` reads `.env`). No issue needed.
6. **Automate off-device SQLite backups with a restore drill** — labels `infrastructure`, `priority: high`. The runbook describes the procedure but nothing validates it; ties to the Pi deployment gap.

---

# Implementation record: rich-text formatting (#7) — closed

Completed and closed on 2026-11-28. Retained for traceability; **not the active assignment**. Issue: [#7](https://github.com/DarioTek/virtual-index-card/issues/7).

## Objective (as delivered)

Rich-text formatting for card notes on both front and back: **bold**, **italic**, **underline**, and a fixed WCAG AA **4-color palette** (`black`, `green`, `red`, `blue`), with overlapping styles, a 5,000 visible-Unicode-code-point limit per side, safe server-side canonicalization/escaping, verbatim preservation of plain-text cards, and full account isolation and CSRF protection.

### Scope as originally planned, and what changed

- The original scope also included a **block-quote toolbar button** and an **orange/pink** palette pair (6 colors).
- **Block quotes were removed** from the toolbar and editor at the user's request; the storage model and renderer still accept `blockquote` blocks so any existing record keeps rendering safely.
- **Orange and pink were removed** at the user's request, leaving the 4 colors above. `tests/test_domain.py` asserts those names are rejected.
- The authoritative description of the delivered design is `TD-015` in `docs/technical-decisions.md`.

## Acceptance criteria (final state)

- [x] Bold, italic, underline, and the four palette colors can be applied and removed on both faces during creation and editing.
- [x] Overlapping inline styles survive save, edit reopen, and reload.
- [x] Formatting renders consistently in Deck Management and Review without changing creation order or Review shuffle order.
- [ ] ~~Shared card-face rendering verified end-to-end for public sharing.~~ Deferred: the shared macro and `render_card_face()` exist and are verified in Management and Review; end-to-end public-view verification belongs to #4 (now the active assignment).
- [x] 5,000 visible Unicode code points accepted, 5,001 rejected, regardless of formatting; empty/whitespace-only formatted content rejected.
- [x] Existing plain-text cards (including v3 databases migrated to v4) retain their exact text; markup-like strings and hostile inputs never execute.
- [x] Formatting controls are keyboard-operable (`Tab`, `Ctrl/Cmd+B/I/U`, arrow keys within the toolbar) with accessible names (`aria-label`/`aria-pressed`), and all four palette colors meet WCAG AA (>= 4.5:1) on both card face backgrounds.
- [x] Account isolation, deck ownership checks, and CSRF protection remain intact for all card endpoints.
- [x] `uv run pytest -q`, `python -m compileall -q src tests`, `node --check src/virtual_index_card/static/app.js`, and `git diff --check` pass; `README.md`, `docs/architecture.md`, and `docs/technical-decisions.md` describe the delivered behavior.

*Removed criteria:* the block-quote and six-color clauses were dropped when those features were removed at the user's request.

## Design decisions (as implemented)

1. **Storage:** `cards.front`/`cards.back` remain plain visible text; nullable `front_rich`/`back_rich` (`TEXT`, schema v4) store a canonical versioned JSON AST, `NULL` for unformatted cards. `POST /api/cards` and `PATCH /api/cards/{id}` stay backwards-compatible with `{front, back}` and accept optional `front_rich`/`back_rich`.
2. **Visible-character counting:** Unicode code points (`len(str)` in Python, `Array.from(str).length` in JS), leading/trailing whitespace trimmed, `\n` between blocks counting as one character.
3. **Palette:** `#172033`, `#066e42`, `#b42318`, `#175cd3`.
4. **Compatibility with #5:** export/import should carry optional `front_rich`/`back_rich` next to plain `front`/`back` for full-fidelity round-trips.

## Validation performed

- `uv run pytest -q` — full suite green with one Starlette/httpx deprecation warning.
- `python -m compileall -q src tests`, `node --check src/virtual_index_card/static/app.js`, `git diff --check` — all clean.
- Pure JS formatting logic exercised via Node. Browser `contenteditable` typing/selection was **not** run in a headless browser (no Chromium/Playwright available), which remains the one unverified area.

## History notes

- Local repository history begins at commit `1d13507`. The branch and commit cited in earlier revisions of this plan (`arena/d38a9b9c-virtual-index-card` at `732bbee`) are not part of this repository's history, so intermediate checkpoints cannot be diffed.
- Test counts recorded during development are omitted here on purpose; run `uv run pytest -q` for the current count.
