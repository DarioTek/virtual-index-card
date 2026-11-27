# Active plan: Multiple decks (#1)

## Objective

Implement support for each account to create and select multiple independent card decks. Newly created decks use the next account-local default name (`My Deck 1`, `My Deck 2`, and so on). Preserve existing users' cards and Review order by migrating them into `My Deck 1`.

## Confirmed scope and decisions

- Issue: [#1 — Create Multiple Decks for Different Topics](https://github.com/DarioTek/virtual-index-card/issues/1).
- Add deck creation and selection to the existing application; deck cards and saved Review order must remain isolated.
- Existing schema-v2 accounts receive one `My Deck 1` containing all their current cards with IDs, content, timestamps, and positions unchanged.
- Newly approved accounts start with an empty `My Deck 1`. Additional decks are created in sequence per account.
- Keep the existing `/` and `/review` URLs; `deck_id` selects the current deck, omitted selection uses that account's first deck, and invalid/foreign IDs return 404.
- Rename/delete/share/import of decks are outside this request and are not included.

## Tasks

| # | Task | Status |
|---|---|---|
| 1 | Confirm issue scope and default naming/migration behavior | Completed |
| 2 | Add schema-v3 decks table and lossless v2 migration | Completed |
| 3 | Add account-owned deck persistence and deck-scoped card/order queries | Completed |
| 4 | Add deck creation/selection UI and carry selected deck through Review and card APIs | Completed |
| 5 | Add migration, multi-deck, isolation, and regression tests | In Progress |
| 6 | Update README, architecture, and technical decision documentation | Completed |
| 7 | Run available validations and review diff | Blocked |
| 8 | Fix regression: card creation from a non-default selected deck | Completed |

## Acceptance criteria

- [ ] New accounts start with one empty `My Deck 1`; creating additional decks names them sequentially (`My Deck 2`, etc.) per account.
- [ ] Authenticated users can select among their decks on management and Review pages and create a deck from the app.
- [ ] Card creation, editing, deletion, listing, shuffle, and saved Review order apply only to the selected deck.
- [ ] Deck IDs belonging to another account cannot be used to view or mutate its cards.
- [ ] Schema-v2 migration creates `My Deck 1` for each account and preserves all existing card data and positions.
- [ ] Existing routes remain usable and choose a safe default deck when no selection is specified.
- [ ] Tests cover fresh schema, migration, naming, selection, deck isolation, and existing single-deck/auth/CSRF behavior.
- [x] Relevant docs describe the implemented multi-deck model; `git diff --check` passes.

## Validation strategy

- Run pytest for repository, migration, and FastAPI integration behavior; run `git diff --check` and JavaScript syntax validation if applicable.
- No Python test dependencies are currently installed (`pytest`, FastAPI, and httpx are unavailable), and `uv` is absent. Do not install packages without the user's approval; report test execution as blocked if this remains the case.
- Inspect migration fixtures and final diff for data preservation, cross-account access, and unintended changes.

## Risks

- Schema migration must preserve every existing card and Review position; test against a representative v2 database.
- Deck selection must be validated against the authenticated account on every route/API call, not trusted from the query string.
- Any legacy endpoint without `deck_id` must resolve only to the authenticated user's default deck.

## Open questions

- None blocking for the requested create/select behavior. Naming is per account and deck rename/delete are intentionally deferred.

## Proposed Issues

Drafts only; no GitHub Issues created or modified.

### Add CI checks for tests and basic quality gates

- **Description:** Add a lightweight automated workflow using the committed lockfile to run tests and suitable syntax checks.
- **Acceptance criteria:** Runs on pull requests and primary-branch pushes; test failures fail the workflow; no secrets are required.
- **Suggested labels:** `automation`, `testing`, `priority: medium`

### Verify HTTPS reverse-proxy deployment on the target host

- **Description:** Exercise the Raspberry Pi runbook and verify proxy, HTTPS/cookie behavior, security headers, and application flows before public exposure.
- **Acceptance criteria:** Record target host/domain; verify HTTP-to-HTTPS redirect, proxy-only app access, secure cookies, and app flows; update the runbook with evidence.
- **Suggested labels:** `deployment`, `security`, `priority: high`

### Automate and rehearse off-device SQLite backups and restore

- **Description:** Configure protected off-device backups and perform a restore drill with retention and recovery steps documented.
- **Acceptance criteria:** Consistent database backup; separate destination; protected access; failure visibility; documented and verified restore procedure.
- **Suggested labels:** `operations`, `data-safety`, `priority: high`

### Add authentication abuse protections and complete a privacy/threat review

- **Description:** Review hosted-notes risks and implement proportionate account-request and login abuse controls with privacy guidance.
- **Acceptance criteria:** Record assets, trust boundaries, and mitigations; test abuse controls and safe failures; document sensitive-data handling and retention.
- **Suggested labels:** `security`, `privacy`, `priority: high`

## Progress log

- 2026-11-27: Issue #1 implementation authorized. User confirmed sequential `My Deck 1`, `My Deck 2`, ... default names. Scope set to deck creation and selection; rename/delete are deferred.
- 2026-11-27: Implemented schema v3 and v2→v3 migration, account-owned deck persistence, deck selector/create form, selected-deck card and Review operations, and regression tests. Existing schema-v2 cards retain IDs, content, timestamps, and positions in `My Deck 1`.
- 2026-11-27: `python -m compileall -q src tests`, `node --check src/virtual_index_card/static/app.js`, and `git diff --check` passed. Manual SQLite/repository smoke checks passed for fresh schema, sequential naming, ownership isolation, v1→v3 and v2→v3 migrations, data/order preservation, foreign keys, and post-migration card ID continuation.
- 2026-11-27: User reported cards created from `My Deck 2` were landing in `My Deck 1`. The cards API intentionally falls back to the first deck when `deck_id` is omitted, so the client must always send the selected deck explicitly. Bound the create form directly to its selected `deck_id`, use that form context in JavaScript, and version the static script URL to avoid a stale cached client. Added a regression assertion for rendered deck context.
- 2026-11-27: `node --check` and a Node harness simulating the form submit passed; the request was `/api/cards?deck_id=2`. Python compilation and `git diff --check` passed. Full pytest remains unavailable because `uv`, pytest, FastAPI, and httpx are absent; dependencies were not installed. Runtime HTTP/template integration remains unverified; task 5 and task 7 remain open/blocked pending a test-capable environment.
