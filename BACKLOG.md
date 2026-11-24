# BACKLOG.md
# Active Project Backlog

## Purpose

This file is the active inventory of work that is not currently being executed in `PLAN.md`.

Use it for future features, defects, technical debt, performance and security improvements, infrastructure work, documentation, and ideas. Completed items are moved to [`docs/backlog-archive.md`](docs/backlog-archive.md) after validation.

**Last reviewed:** 2026-11-24

## Backlog Summary

Update these counts whenever the backlog changes.

| Status | Count |
|---|---:|
| Proposed | 8 |
| Ready | 12 |
| In Progress | 0 |
| Blocked | 0 |
| Deferred | 3 |
| **Total active items** | **23** |

Completed items belong in [`docs/backlog-archive.md`](docs/backlog-archive.md) and are not counted here.

## Conventions

### Priority
- **Critical** — urgent risk, severe defect, or essential operational issue.
- **High** — significant value or risk; prioritize soon.
- **Medium** — useful improvement with normal priority.
- **Low** — optional improvement or idea.

### Status
- **Proposed** — captured but not yet assessed or accepted.
- **Ready** — sufficiently understood and ready to be selected.
- **In Progress** — selected for active work; also reference it in `PLAN.md`.
- **Blocked** — cannot proceed until a dependency or decision is resolved.
- **Deferred** — intentionally postponed.

### ID convention
Assign stable, sequential IDs: `BL-001`, `BL-002`, `BL-003`, and so on. Check both this file and the archive before assigning an ID. Never reuse an ID.

## Active Backlog

### Features and Enhancements

### BL-001: Support multiple named decks

- **Category:** Feature
- **Priority:** High
- **Status:** Proposed
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Let users create, rename, and switch between separate decks so that different subjects do not share one card pool.
- **Expected outcome:** A deck selector and per-deck card lists; shuffle affects only the selected deck.
- **Acceptance criteria:**
  - [ ] A user can create, rename, and delete a deck without losing cards in other decks.
  - [ ] Cards belong to exactly one deck and appear only there.
  - [ ] Shuffling one deck leaves the order of other decks unchanged.
- **Dependencies:** Requires the storage schema work in `BL-010`.
- **Related files/components:** Domain model, repository, deck UI.
- **Notes:** Explicitly out of scope for the initial single-deck release described in `PLAN.md`.
- **Plan reference:** None — not selected.

### BL-002: Add tags and search across cards

- **Category:** Feature
- **Priority:** Medium
- **Status:** Proposed
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Allow cards to carry tags and let users filter or search by front/back text and tag.
- **Expected outcome:** Users can find a card without scrolling through the entire deck.
- **Acceptance criteria:**
  - [ ] A card can have zero or more tags, editable alongside front/back text.
  - [ ] Search matches front text, back text, and tags, case-insensitively.
  - [ ] Clearing a search restores the full deck order.
- **Dependencies:** `BL-001` is helpful but not required.
- **Related files/components:** Card model, repository queries, deck UI.
- **Notes:** Keep search local; no external search service.
- **Plan reference:** None — not selected.

### BL-003: Import and export cards as JSON or CSV

- **Category:** Feature
- **Priority:** High
- **Status:** Ready
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Give users a portable way to back up and move their cards, since the hosted app's database is not directly inspectable.
- **Expected outcome:** A downloadable export and an import flow that validates input before writing data.
- **Acceptance criteria:**
  - [ ] Export produces a valid JSON or CSV file containing front text, back text, and order.
  - [ ] Import rejects malformed files with a clear, non-destructive error.
  - [ ] Importing a previously exported file recreates the same cards and order.
- **Dependencies:** None; should use the same repository API as normal CRUD.
- **Related files/components:** API endpoints, repository, settings UI.
- **Notes:** Data portability is the main mitigation for database lock-in.
- **Plan reference:** None — not selected.

### BL-004: Support Markdown or rich-text notes

- **Category:** Feature
- **Priority:** Medium
- **Status:** Proposed
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Let users format notes (lists, emphasis, code) instead of storing plain text only.
- **Expected outcome:** Rendered formatting on both sides of a card with safe handling of user input.
- **Acceptance criteria:**
  - [ ] Common Markdown syntax renders on the front and back.
  - [ ] Raw HTML and script-like input cannot execute.
  - [ ] Editing a card restores the original Markdown source, not rendered HTML.
- **Dependencies:** Security review in `BL-013`.
- **Related files/components:** Card rendering, input validation, tests.
- **Notes:** Deferred from MVP so escaping behavior can be established first.
- **Plan reference:** None — not selected.

### BL-005: Undo and redo for delete and shuffle

- **Category:** Feature
- **Priority:** High
- **Status:** Ready
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Recover from accidental deletion or an unwanted shuffle without editing the database by hand.
- **Expected outcome:** An undo action restores the previous card set or card order; redo reapplies it.
- **Acceptance criteria:**
  - [ ] After deleting a card, undo restores it with its original front, back, and position.
  - [ ] After shuffling, undo restores the exact prior order.
  - [ ] Redo reapplies the most recently undone action.
  - [ ] Undo state does not survive an application restart unless explicitly persisted.
- **Dependencies:** None.
- **Related files/components:** Command/undo layer, API, UI controls.
- **Notes:** MVP uses an explicit delete confirmation instead; this item adds real undo.
- **Plan reference:** None — not selected.

### BL-006: Guided study session mode

- **Category:** Feature
- **Priority:** Medium
- **Status:** Proposed
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Add a focused mode that walks through cards one at a time and tracks known/unknown answers.
- **Expected outcome:** Users can run a study pass and see which cards need review.
- **Acceptance criteria:**
  - [ ] Cards are presented one at a time in shuffled order.
  - [ ] Users can mark a card as known or needs review.
  - [ ] Session progress and results are visible at the end.
- **Dependencies:** `BL-005` is useful for accidental exits.
- **Related files/components:** New study UI, session state.
- **Notes:** Separate from simple deck shuffling in the MVP.
- **Plan reference:** None — not selected.

### BL-007: Card themes and printable view

- **Category:** Feature
- **Priority:** Low
- **Status:** Proposed
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Let users change card appearance and print a deck on physical index-card stock.
- **Expected outcome:** Theme selection and a print stylesheet that lays out front/back content predictably.
- **Acceptance criteria:**
  - [ ] At least one alternative theme is selectable and persists.
  - [ ] Print preview shows one card per expected printable area without clipped text.
  - [ ] Screen flip animation does not interfere with printed output.
- **Dependencies:** None.
- **Related files/components:** CSS, settings UI.
- **Notes:** Cosmetic; keep after functional foundations.
- **Plan reference:** None — not selected.

### BL-008: Full keyboard and screen-reader support for card interactions

- **Category:** Feature
- **Priority:** High
- **Status:** Ready
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Extend the MVP's accessible flip button to complete keyboard navigation and assistive-technology announcements for all card actions.
- **Expected outcome:** All core actions are discoverable and operable without a mouse, with understandable state announcements.
- **Acceptance criteria:**
  - [ ] Tab order reaches every card action in a logical sequence.
  - [ ] Flip state is exposed with appropriate `aria` attributes and announced on change.
  - [ ] Create, edit, delete, and shuffle are operable by keyboard alone.
  - [ ] A screen-reader smoke test is documented with results.
- **Dependencies:** None.
- **Related files/components:** Templates, JS, CSS.
- **Notes:** MVP already includes a button-based flip; this item completes the broader accessibility work.
- **Plan reference:** None — not selected.

### BL-009: Cloud sync and multi-device access

- **Category:** Feature
- **Priority:** Medium
- **Status:** Deferred
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Sync decks across devices through a remote service.
- **Expected outcome:** Cards edited on one device appear on another without manual file transfer.
- **Acceptance criteria:**
  - [ ] Changes sync bidirectionally with a documented conflict-resolution rule.
  - [ ] Offline edits are queued and applied on reconnect.
  - [ ] Users can opt out of all remote storage.
- **Dependencies:** `BL-010`, `BL-013`, and an authentication decision that does not yet exist.
- **Related files/components:** Sync service, auth, repository.
- **Notes:** Intentionally deferred; the MVP is a hosted, single-user deployment pending the access decision in `BL-021`.
- **Plan reference:** None — not selected.

### Bugs and Defects

_No items yet. No released code exists to contain defects. New issues should be recorded here with reproduction steps._

### Technical Debt and Refactoring

### BL-010: Define SQLite schema versioning and migration strategy

- **Category:** Technical Debt
- **Priority:** High
- **Status:** Ready
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Establish how the SQLite schema is created, versioned, and upgraded before real user data exists.
- **Expected outcome:** A fresh install and an upgrade from a previous schema both produce a usable database without data loss.
- **Acceptance criteria:**
  - [ ] A schema version is stored in the database.
  - [ ] Applying the current schema to an empty database is automated.
  - [ ] At least one upgrade path is covered by a test using a fixture database.
  - [ ] Unsupported versions fail with an actionable message and do not overwrite existing data.
- **Dependencies:** None; best done before the first persisted release.
- **Related files/components:** Repository, migration module, tests.
- **Notes:** The MVP creates the initial schema; this item adds durable upgrade support.
- **Plan reference:** None — not selected.

### BL-011: Extract a reusable framework-independent domain package

- **Category:** Technical Debt
- **Priority:** Low
- **Status:** Ready
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Keep `Card`, deck ordering, and shuffle logic independent of the web framework so importers, tests, or a future client can reuse them.
- **Expected outcome:** Domain modules import and test without FastAPI or an HTTP client.
- **Acceptance criteria:**
  - [ ] Domain tests import only domain modules, not HTTP or UI modules.
  - [ ] API handlers delegate ordering and shuffle decisions to domain functions.
  - [ ] No behavior changes in existing tests after extraction.
- **Dependencies:** Initial implementation of the domain layer.
- **Related files/components:** `src/` domain modules, API handlers, tests.
- **Notes:** The proposed architecture already keeps layers separate; this item verifies and hardens that boundary.
- **Plan reference:** None — not selected.

### Performance and Scalability

### BL-012: Handle very large decks without rendering every card

- **Category:** Performance
- **Priority:** Low
- **Status:** Proposed
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Avoid slow page loads and janky flip animations when a deck contains thousands of cards.
- **Expected outcome:** Browsing and shuffling remain responsive as deck size grows.
- **Acceptance criteria:**
  - [ ] A deck of 1,000 cards renders and flips without a measurable UI freeze in a manual check.
  - [ ] Rendering is limited to a viewport-sized window or paginated subset.
  - [ ] Shuffle still randomizes the whole deck, not just the visible subset.
- **Dependencies:** `BL-017` for repeatable measurement.
- **Related files/components:** Deck UI, repository queries.
- **Notes:** Probably unnecessary for personal note collections; measure before implementing.
- **Plan reference:** None — not selected.

### Security and Privacy

### BL-013: Threat model and privacy review before any network exposure

- **Category:** Security
- **Priority:** Medium
- **Status:** Ready
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Document trust boundaries and verify that personal notes cannot leak through rendered HTML, logs, or unintended network calls before deployment.
- **Expected outcome:** A short review record and concrete fixes for any findings.
- **Acceptance criteria:**
  - [ ] Data flows and trust boundaries are documented.
  - [ ] User note content is rendered as text, never interpreted as HTML, and is not logged.
  - [ ] The app makes no third-party network requests.
  - [ ] Findings are either fixed or explicitly accepted with rationale.
- **Dependencies:** None for local review; must precede `BL-009`.
- **Related files/components:** Templates, logging, documentation.
- **Notes:** The app is hosted, so this is a release gate rather than future work.
- **Plan reference:** None — not selected.

### BL-014: Optional encryption at rest or PIN lock

- **Category:** Security
- **Priority:** Medium
- **Status:** Deferred
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Protect notes on shared machines with an optional lock or encrypted local store.
- **Expected outcome:** Users can require authentication before the deck is readable.
- **Acceptance criteria:**
  - [ ] Enabling a PIN blocks access to card content until it is entered.
  - [ ] Lost PIN behavior is documented.
  - [ ] Encrypted data remains readable after a normal application update.
- **Dependencies:** `BL-013`; likely `BL-009` if keys are managed remotely.
- **Related files/components:** Repository, settings UI, key management.
- **Notes:** Deferred because it adds significant recovery complexity to a local MVP.
- **Plan reference:** None — not selected.

### Infrastructure, DevOps, and Automation

### BL-015: Continuous integration checks

- **Category:** Infrastructure
- **Priority:** Medium
- **Status:** Ready
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Run lint, type checks where applicable, and the pytest suite automatically on pushes and pull requests.
- **Expected outcome:** Broken changes are visible before review instead of failing locally at random.
- **Acceptance criteria:**
  - [ ] A CI workflow runs on pushes and pull requests to the working branch and `main`.
  - [ ] Tests and lint/format checks fail the workflow when they fail locally.
  - [ ] The workflow uses the same dependency setup documented in `README.md`.
- **Dependencies:** A dependency manifest and test suite from initial implementation.
- **Related files/components:** `.github/workflows/`, `pyproject.toml`, `README.md`.
- **Notes:** Not needed for the documentation-only assignment.
- **Plan reference:** None — not selected.

### BL-016: Repeatable deployment package for the hosted app

- **Category:** Infrastructure
- **Priority:** Low
- **Status:** Ready
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Package the hosted app so releases can be deployed consistently without manual source edits on the server.
- **Expected outcome:** A container image or documented service deployment that starts the app with a persistent SQLite volume.
- **Acceptance criteria:**
  - [ ] A fresh server can deploy the app using documented commands only.
  - [ ] The SQLite database survives a normal application update.
  - [ ] The deployment method is verified on at least one clean environment.
- **Dependencies:** Stable application entry point from initial implementation.
- **Related files/components:** Container/service config, deployment documentation, `README.md`.
- **Notes:** `uv run` is fine for development; this item covers production-style deployment.
- **Plan reference:** None — not selected.

### Testing and Quality

### BL-017: Browser end-to-end tests for the four core flows

- **Category:** Testing
- **Priority:** Medium
- **Status:** Ready
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Automate create, flip, edit/delete, and shuffle in a real browser so UI regressions are caught without manual repetition.
- **Expected outcome:** A repeatable browser test suite covering the product's core behavior.
- **Acceptance criteria:**
  - [ ] Tests create a card with front/back content and verify both sides render.
  - [ ] Tests flip the card and assert the visible side changes.
  - [ ] Tests edit and delete a card and verify persistence after reload.
  - [ ] Tests shuffle and assert each card appears exactly once.
  - [ ] Tests run in CI with an isolated SQLite test database.
- **Dependencies:** Initial UI implementation; `BL-015` for CI execution.
- **Related files/components:** `tests/`, browser test configuration.
- **Notes:** Manual smoke checks are sufficient for the first release.
- **Plan reference:** None — not selected.

### BL-018: Property-based tests for shuffle behavior

- **Category:** Testing
- **Priority:** Low
- **Status:** Proposed
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Verify shuffle invariants across many generated deck sizes rather than a handful of fixed examples.
- **Expected outcome:** Higher confidence that shuffle never drops or duplicates cards.
- **Acceptance criteria:**
  - [ ] Generated decks of varied sizes always return the same multiset of card IDs.
  - [ ] An injectable RNG makes every test reproducible.
  - [ ] A basic distribution check catches a frequently broken or constant shuffle.
- **Dependencies:** Domain shuffle implementation.
- **Related files/components:** Domain tests.
- **Notes:** Unit tests with a fixed seed cover the MVP; this adds broader coverage.
- **Plan reference:** None — not selected.

### Documentation and Developer Experience

### BL-019: User guide and as-built architecture refresh

- **Category:** Documentation
- **Priority:** Medium
- **Status:** Ready
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Replace the proposed architecture with the as-built version and add a short user guide once the MVP exists.
- **Expected outcome:** Documentation matches the running app and supports a new user through the core flows.
- **Acceptance criteria:**
  - [ ] `docs/architecture.md` no longer labels implemented components as proposals.
  - [ ] `README.md` lists verified install, run, and test commands.
  - [ ] A user guide covers create, flip, edit, delete, and shuffle with screenshots or equivalent description.
- **Dependencies:** First implemented release.
- **Related files/components:** `README.md`, `docs/architecture.md`, new guide.
- **Notes:** Current docs intentionally describe a proposal only.
- **Plan reference:** None — not selected.

### Research and Ideas

### BL-020: Evaluate hosting options for the deployed app

- **Category:** Research
- **Priority:** Low
- **Status:** Proposed
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Compare simple VPS/systemd hosting, a container platform, and a platform-as-a-service option for the server-side app.
- **Expected outcome:** A short decision note with trade-offs for cost, operations, SQLite persistence, and backups.
- **Acceptance criteria:**
  - [ ] A written comparison covers setup effort, persistent storage, TLS, backups, and scaling limits.
  - [ ] A recommendation states a default hosting target for the first deployment.
  - [ ] No production code changes are made as part of the research.
- **Dependencies:** None; informs `BL-016` and `BL-022`.
- **Related files/components:** `docs/technical-decisions.md`.
- **Notes:** SQLite needs a persistent filesystem, which affects hosting choice.
- **Plan reference:** None — not selected.

### BL-022: HTTPS and reverse-proxy deployment configuration

- **Category:** Infrastructure
- **Priority:** High
- **Status:** Ready
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Serve the hosted app over TLS with a reverse proxy, redirect plain HTTP, and set basic security headers.
- **Expected outcome:** The deployed app is reachable only over HTTPS with documented certificate handling.
- **Acceptance criteria:**
  - [ ] The app is reachable over HTTPS with a valid certificate.
  - [ ] HTTP requests redirect to HTTPS.
  - [ ] Basic security headers are configured and verified.
  - [ ] Deployment steps are documented without embedding secrets in the repository.
- **Dependencies:** `BL-021` for access control before public exposure; `BL-020` for hosting target.
- **Related files/components:** Reverse-proxy config, deployment documentation.
- **Notes:** Required before the app is exposed beyond a private network.
- **Plan reference:** None — not selected.

### BL-023: Scheduled SQLite backups and restore drill

- **Category:** Infrastructure
- **Priority:** High
- **Status:** Ready
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Protect the hosted database with automated backups stored outside the application filesystem, and verify that a restore works.
- **Expected outcome:** A recent backup can be restored with a documented procedure and without data loss.
- **Acceptance criteria:**
  - [ ] Backups of the SQLite file run on a defined schedule.
  - [ ] Backups are stored separately from the running application and are not committed to Git.
  - [ ] A restore from a real backup is tested and documented.
  - [ ] Backup success and failure are observable.
- **Dependencies:** `BL-022` deployment configuration and `BL-020` hosting target.
- **Related files/components:** Deployment scripts, operations documentation.
- **Notes:** SQLite removes server-database complexity but makes file-level backup discipline essential.
- **Plan reference:** None — not selected.

### BL-024: Password reset and email verification

- **Category:** Feature
- **Priority:** Medium
- **Status:** Deferred
- **Date added:** 2026-11-24
- **Last updated:** 2026-11-24
- **Description:** Add account recovery and verify email ownership for registered users.
- **Expected outcome:** Users can recover access to their account and email addresses are confirmed.
- **Acceptance criteria:**
  - [ ] A password reset request creates a single-use, expiring token delivered out of band.
  - [ ] Reset tokens cannot be reused and expire as documented.
  - [ ] Unverified accounts have limited access until email verification succeeds.
- **Dependencies:** `BL-021` account foundation and a mail delivery decision.
- **Related files/components:** Auth module, token store, email integration, templates.
- **Notes:** Deferred; basic registration, login, and logout are delivered under `BL-021`.
- **Plan reference:** None — not selected.

## Backlog Maintenance Rules

1. Search this file and `docs/backlog-archive.md` for duplicates before creating an item.
2. Keep each item small enough to estimate and implement.
3. Write acceptance criteria that can be verified.
4. Update priority and status when circumstances change.
5. Record dependencies explicitly.
6. When selected, reference the backlog ID in `PLAN.md` and change status to `In Progress`.
7. Mark an item complete only after implementation and validation.
8. Move completed items, including their full details, to `docs/backlog-archive.md`; add a completion date and validation/delivery reference.
9. Remove archived items from this active file and refresh the summary counts.
10. Preserve IDs permanently. If an archived item is reopened, restore it here using its original ID and document why.
11. Do not treat this backlog as authorization to implement work.
