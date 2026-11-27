# Active plan: Complete multiple-deck management (#1)

## Objective

Deliver the full [multiple-deck epic #1](https://github.com/DarioTek/virtual-index-card/issues/1) through its child issues: custom names and rename (#2), safe empty-deck deletion (#3), revocable public read-only links (#4), and versioned JSON import/export (#5). Preserve existing card data, account isolation, and per-deck Review order throughout.

## Confirmed scope and decisions

- #1 is the epic and remains open until #2–#5 are complete, their pull requests are merged, the complete automated suite passes, and documentation is current.
- The existing schema-v3 multiple-deck implementation is the baseline: new and upgraded accounts receive `My Deck 1`; cards and Review order are deck-scoped.
- Deck names are trimmed, non-empty, at most 100 characters, and case-insensitively unique per account. Generated `My Deck N` names remain available.
- Only empty decks may be deleted, and an account must retain at least one deck.
- Public sharing is anonymous, unlisted, read-only, revocable, and valid until revoked or rotated. Public users cannot persist shuffle or any other mutation.
- Import/export uses versioned full-fidelity JSON. Import creates a new deck, never overwrites, is atomic, and observes documented configurable byte/card limits.
- A complete passing automated suite is sufficient; manual browser testing is not a closure requirement.
- `PROJECT_GUIDELINES.md` is not present. The Definition of Done is the completion checklist in `AGENTS.md` plus the issue acceptance criteria.

## Delivery order and tasks

| # | Task | Related issue | Likely components | Status |
|---|---|---|---|---|
| 1 | Re-establish a test-capable environment and verify the existing multi-deck baseline | #1 | dependency environment, complete test suite | Completed |
| 2 | Add validated custom deck creation and account-scoped rename, including concurrency-safe uniqueness | #2 | `domain.py`, `repository.py`, `app.py`, deck template, tests | Completed |
| 3 | Add transactional empty-deck deletion with last-deck protection and confirmation UI | #3 | `repository.py`, `app.py`, deck template, tests | Not Started |
| 4 | Design and migrate storage for hashed public-share tokens; add owner controls and anonymous read-only Review | #4 | `db.py`, `security.py`, `repository.py`, `app.py`, templates, tests | Not Started |
| 5 | Define the versioned JSON format and configurable limits; add transactional export/import | #5 | `config.py`, `domain.py`, `repository.py`, `app.py`, templates, tests, docs | Not Started |
| 6 | Run full regression/security/migration validation and reconcile all documentation | #1–#5 | tests, README, architecture, technical decisions | Not Started |
| 7 | Review the final diff and prepare issue-linked commit/pull-request reporting | #1–#5 | repository and GitHub metadata | Not Started |

Each child issue will be implemented as a focused logical unit in dependency order. Status will be updated before and after each unit.

## Acceptance criteria

### Existing core and migration

- [x] New accounts start with exactly one empty `My Deck 1`; generated names remain sequential per account.
- [x] CRUD, Review, and persisted shuffle are isolated to the selected deck.
- [x] Invalid or foreign deck IDs fail without disclosing another account's data.
- [x] Existing schema-v2 migration preserves card IDs, ownership, content, timestamps, and Review positions.

### #2 — custom names and rename

- [x] Valid custom names can be supplied during creation and existing owned decks can be renamed.
- [x] Names are trimmed, 1–100 characters, and unique per account case-insensitively; the database constraint is authoritative for conflicting writes.
- [x] Rename preserves cards, timestamps, and Review order; foreign deck IDs fail safely.

### #3 — empty-deck deletion

- [ ] An owner can delete an empty non-last deck after confirmation.
- [ ] Non-empty, last, foreign, and nonexistent deck deletion attempts are rejected transactionally.
- [ ] Any associated public link is invalid after eligible deletion.

### #4 — public read-only sharing

- [ ] Owners can generate, rotate, and revoke unlisted links backed by unguessable tokens not stored in plaintext where avoidable.
- [ ] Anonymous viewers can view, navigate, and flip only the shared deck without persisting changes.
- [ ] Invalid/revoked links and all mutation attempts fail safely without account or deck information leakage.

### #5 — JSON import/export

- [ ] Owned decks export to documented, versioned JSON without credentials, internal ownership IDs, sessions, or sharing tokens.
- [ ] Import creates a new uniquely named deck and round-trips card text and Review order.
- [ ] Malformed, incompatible, invalid, collision-prone, or over-limit imports fail atomically.
- [ ] Upload-byte and card-count limits are configurable and documented with defaults.

### Definition of Done

- [ ] Focused unit/integration/security/migration tests cover success, boundary, ownership, and error paths. (#2 coverage complete; #3–#5 pending.)
- [ ] `uv run pytest -q`, JavaScript syntax validation, Python compilation, and `git diff --check` pass.
- [ ] README, architecture, technical decisions, configuration, and operator guidance describe the as-built behavior.
- [ ] No unrelated changes, generated artifacts, secrets, or database files are included.
- [ ] Child work is linked to issues/PRs as authorized; #1 is not closed before all child PRs merge.

## Validation strategy

1. Establish the baseline with `uv sync --group dev` and `uv run pytest -q` before feature changes.
2. For each child issue, add repository/domain tests first where practical, then HTTP integration and authorization/error-path coverage.
3. Re-run focused tests during implementation and the complete suite at every child milestone.
4. Validate schema upgrades with representative old databases and verify transactional rollback for destructive/import operations.
5. Run `python -m compileall -q src tests`, `node --check src/virtual_index_card/static/app.js`, and `git diff --check` before completion.
6. Inspect the final diff and Git status for unrelated or sensitive files.

## Dependencies and risks

- #2 should precede #5 because imported names use the same validation and uniqueness rules.
- #3 must integrate with #4 so deletion invalidates public access.
- #4 requires a schema migration and expands the unauthenticated attack surface; token storage, cache behavior, and non-disclosure need security-focused review.
- #5 processes untrusted input; byte/card limits, schema validation, and an all-or-nothing transaction are required.
- SQLite write concurrency may expose naming or last-deck race conditions; database constraints and transactional checks must be authoritative.
- Existing installations are durable-data systems. Every schema migration must preserve data and fail loudly on unsupported versions.

## Open questions

- None currently blocking. Defaults for configurable import limits and the exact JSON schema version will be selected during #5, documented, and covered by tests.

## Progress log

- 2026-11-27: Original multiple-deck creation/selection, schema-v3 migration, deck-scoped CRUD/Review/shuffle, and supporting documentation were implemented on the baseline commit. A selected-deck card-creation regression was fixed. Full pytest had not been run in that earlier environment.
- 2026-11-27: #1 was expanded and groomed as an epic. Child issues #2–#5, repository-wide priority labels, and the `Multiple Deck Support` milestone were created.
- 2026-11-27: User authorized starting #1. Re-read the live epic and child issues, confirmed a clean branch, replaced the obsolete plan with this dependency-ordered delivery plan, and began restoring baseline test validation.
- 2026-11-27: System Python correctly rejected a user-level `pip install uv` under PEP 668. Installed `uv` in an isolated `/tmp` bootstrap environment, synchronized the committed development environment, and ran the baseline suite. The first run found one stale empty-Review copy assertion (67 passed, 1 failed); updated it to the implemented deck-specific message.
- 2026-11-27: Completed #2 implementation: shared 100-character name validation, optional custom creation, sequential generation beyond existing numeric names, account-scoped rename, database-backed case-insensitive uniqueness errors, form UI, ownership/CSRF handling, tests, and documentation. Focused tests passed (29); the complete suite passed (72) with one existing Starlette/httpx deprecation warning. Python compilation, JavaScript syntax validation, and `git diff --check` also passed. Next: implement transactional empty-deck deletion for #3.
