# Active plan: Add formatting to flash-card text (#7)

## Objective

Implement rich-text formatting for flash-card notes on [GitHub Issue #7](https://github.com/DarioTek/virtual-index-card/issues/7) so card authors can apply, overlap, and remove **bold**, **italic**, **underline**, **block quotes**, and a fixed accessible **6-color palette** (black, green, red, orange, blue, pink) on both front and back faces during card creation and editing. Preserve existing plain-text cards verbatim, enforce the 5,000-visible-character limit per side, prevent XSS/active-content execution, and maintain full account isolation, CSRF protection, keyboard accessibility, and responsive design.

## Confirmed scope and proposed design decisions

### In scope (#7)
- Visual formatting toolbar controls for **bold**, **italic**, **underline**, **block quote**, and **text color** (`black`, `green`, `red`, `orange`, `blue`, `pink`) on both **Front** and **Back** in the card-creation form and inline card-edit forms (`deck.html`).
- Overlapping inline styles (e.g., bold + italic + underline + color) and inline styles combined with block quotes, preserved across save, edit reopen, and reload.
- Consistent formatted rendering in **Deck Management** (`/`), **Edit** pre-population, and **Review** (`/review`) without changing card ordering or Review shuffle order.
- Strict server-side sanitization/canonicalization and visible-character limit validation (5,000 max per side, 5,001 rejected regardless of formatting markup).
- Safe preservation of existing plain-text cards without interpreting `<`, `>`, `&`, or markup-like strings as HTML.
- Keyboard-operable formatting controls with accessible names (`aria-label`, `aria-pressed`, toolbar semantics) and WCAG AA (>= 4.5:1) color contrast against both front (`#fffefa`) and back (`#edf8f6`) card backgrounds.
- Additive SQLite schema migration (`v3 -> v4`) and documentation updates (`README.md`, `docs/architecture.md`, `docs/technical-decisions.md`).

### Out of scope
- Images, links, tables, font family/size selection, headings, lists, and arbitrary custom colors.
- Implementing public sharing (#4) or JSON import/export (#5) themselves (tracked separately; #7 only ensures a compatible shared renderer and storage model).

### Proposed resolutions for Issue #7 open questions (pending approval)
1. **Storage & API compatibility (additive schema v4):**
   - Keep `cards.front` and `cards.back` as plain visible text (`TEXT NOT NULL`) and add nullable `front_rich` and `back_rich` (`TEXT`) columns storing a canonical JSON rich-text AST (list of `{type: "paragraph" | "blockquote", runs: [{text, bold?, italic?, underline?, color?}]}`).
   - Existing plain-text cards keep `front_rich = NULL` / `back_rich = NULL` and render strictly via Jinja auto-escaping, guaranteeing markup-like plain text (`<script>alert(1)</script>`, `2 < 3`) is never interpreted as markup.
   - `POST /api/cards` and `PATCH /api/cards/{id}` remain backwards-compatible for `{front, back}` plain-text callers while accepting optional `front_rich` / `back_rich` (or sanitized canonical rich payload). The server never trusts raw client HTML: it validates/canonicalizes the structured document on an allowlist, derives trimmed plain visible text, and rejects empty or >5,000-character sides.
   - Rendering runs through a single safe helper/Jinja macro using semantic phrasing elements and CSS classes (`strong`, `em`, `u`, `span.fmt-block`, `span.fmt-quote`, `span.fmt-color-*` — valid inside `<button class="flip-button">` without inline `style` attributes), so future public sharing (#4) will automatically render formatting identically in read-only mode.
2. **Multi-line block quotes:**
   - Treat block quote as a **block-level** toggle affecting every paragraph/line intersecting the selection. If all selected blocks are already block quotes, toggling unwraps them to normal paragraphs; otherwise all selected blocks become block quotes. Consecutive quoted lines preserve line breaks and support overlapping inline styles inside the quote.
3. **Visible-character counting convention:**
   - Count **Unicode code points** (`len(str)` in Python, `Array.from(str).length` in JavaScript), with leading/trailing whitespace trimmed and `\n` between blocks counting as 1 character — matching existing `MAX_NOTE_LENGTH = 5000` in `domain.py`.
4. **Accessible 6-color palette (WCAG AA >= 4.5:1 on both `#fffefa` and `#edf8f6`):**
   - `black` (`#172033`), `green` (`#066e42`), `red` (`#b42318`), `orange` (`#9a4600`), `blue` (`#175cd3`), `pink` (`#a51863`).
5. **Compatibility with JSON import/export (#5):**
   - Recommend documenting that #5 should include optional `front_rich` / `back_rich` fields in its versioned JSON schema alongside plain `front` / `back` so exported formatted decks round-trip with full fidelity.

## Delivery order and tasks

| # | Task | Related issue | Likely components | Status |
|---|---|---|---|---|
| 1 | Approve design decisions for storage, multi-line block quotes, code-point counting, and palette shades | #7 | `PLAN.md`, `docs/technical-decisions.md` | Completed |
| 2 | Restore test-capable Python environment (`uv` / `.venv`) and verify baseline tests pass | #7 | local `.venv` (untracked) | Completed |
| 3 | Design and implement rich-text domain model, canonicalization/sanitization, Unicode code-point visible-length validation, and safe HTML rendering | #7 | `src/virtual_index_card/domain.py`, `src/virtual_index_card/formatting.py` | Completed |
| 4 | Add additive SQLite schema v4 migration (`front_rich`, `back_rich`) and update repository queries while preserving plain-text cards | #7 | `src/virtual_index_card/db.py`, `src/virtual_index_card/repository.py` | Completed |
| 5 | Update card API (`POST /api/cards`, `PATCH /api/cards/{id}`) and templates (`deck.html`, `review.html`, shared card-face partial/macro) with backwards compatibility | #7 | `src/virtual_index_card/app.py`, `src/virtual_index_card/templates/` | Completed |
| 6 | Build accessible rich-text editor toolbar and selection/formatting logic in JS + responsive CSS styles for toolbar, overlapping marks, block quotes, and accessible color palette | #7 | `src/virtual_index_card/static/app.js`, `src/virtual_index_card/static/styles.css`, `src/virtual_index_card/templates/deck.html` | Completed |
| 7 | Add comprehensive unit, migration, API, security/XSS, accessibility/contrast, and UI-integration tests | #7 | `tests/test_domain.py`, `tests/test_repository.py`, `tests/test_app.py`, `tests/test_admin.py` | Completed |
| 8 | Run full test suite, Python compile check, JS syntax check, contrast verification, and `git diff --check`; update `README.md`, `docs/architecture.md`, `docs/technical-decisions.md`, and `PLAN.md` | #7 | `README.md`, `docs/*.md`, `PLAN.md` | Completed |

## Acceptance criteria

- [x] On both front and back, a user can apply and remove **bold**, **italic**, **underline**, **block-quote** styling, and any of the six palette colors (**black, green, red, orange, blue, pink**) during card creation and editing.
- [x] Overlapping inline styles and block-quote + inline combinations remain applied to the intended text after saving, reopening for editing, and reloading.
- [x] Formatting displays consistently in **Deck Management** and **Review** views without changing card creation order or Review shuffle order.
- [ ] Shared card-face rendering uses the sanitized canonical representation so future public sharing (#4) displays saved formatting in read-only mode without granting edit access. *(Shared macro `card_faces` and `render_card_face` are implemented and verified in Management and Review; end-to-end public-view verification awaits #4 implementation.)*
- [x] A side with **5,000** visible Unicode code points is accepted; one with **5,001** is rejected, regardless of formatting complexity; empty/whitespace-only formatted content is rejected.
- [x] Existing plain-text cards (including v3 databases migrated to v4) retain their exact text; markup-like strings (`<b>`, `<script>`, etc.) and hostile inputs never execute.
- [x] Formatting controls are keyboard-operable (`Tab`, arrow keys within toolbar, `Enter`/`Space`, `Ctrl/Cmd+B/I/U` shortcuts) with accessible names (`aria-label`/`aria-pressed`), and all six palette colors meet WCAG AA (>= 4.5:1) contrast on both card face backgrounds.
- [x] Account isolation, deck ownership checks, and CSRF protections remain intact for all card endpoints.
- [x] Complete automated test suite (`uv run pytest -q`: 90 passed), `python -m compileall -q src tests`, `node --check src/virtual_index_card/static/app.js`, and `git diff --check` pass, and `README.md`, `docs/architecture.md`, and `docs/technical-decisions.md` accurately describe the delivered behavior.

## Validation strategy

1. **Domain & sanitization unit tests:** Verify AST parsing/canonicalization, overlapping marks, multi-line block quotes, Unicode code-point visible length boundaries (`5000` accepted, `5001` rejected, empty/whitespace rejected, emoji/multi-byte counting), hostile/unsupported tags/attributes stripped or rejected, and deterministic safe rendering.
2. **Database & migration tests:** Verify fresh schema v4 creation, v1/v2/v3 -> v4 migrations preserving existing plain-text cards (`front_rich IS NULL`, `back_rich IS NULL`) and card IDs/positions/ownership, and `PRAGMA foreign_key_check`.
3. **API, security & isolation tests:** Verify creating/editing cards with plain text and rich formatting on both sides, backwards compatibility with `{front, back}`, rejection of hostile payloads (`<script>`, `onerror=`, `javascript:`, disallowed colors/tags), 422 on 5,001 visible chars, 403 without CSRF, and 404 across accounts/decks.
4. **Template, accessibility & contrast checks:** Verify rendered management, edit, and review HTML contains expected accessible toolbar attributes (`role="toolbar"`, `aria-label`, `aria-pressed`), palette class rendering, plain-text literal escaping, and mathematical WCAG AA (>= 4.5:1) contrast ratio checks for all 6 palette shades against card front and back backgrounds.
5. **JS & static checks:** Run `node --check src/virtual_index_card/static/app.js`, `python -m compileall -q src tests`, `uv run pytest -q`, and `git diff --check`. Also exercise the rich-text editor in a headless/live check if available, or document any browser-only interaction checks not automated.

## Dependencies and risks

- **Browser `contenteditable` inconsistencies:** Native `document.execCommand` behaves differently across browsers for overlapping tags, color spans, and block quotes. Mitigation: build explicit DOM/Range normalization and canonical JSON AST serialization in `app.js` so the editor produces clean, predictable formatting and survives save/edit round-trips reliably.
- **HTML validity inside `<button class="flip-button">`:** Flow elements (`<p>`, `<blockquote>`) are invalid inside `<button>`. Mitigation: render block containers as `<span class="fmt-block">` / `<span class="fmt-quote">` (`display: block`) with phrasing tags (`<strong>`, `<em>`, `<u>`, `<span class="fmt-color-*">`) so HTML5 remains valid and existing flip interaction/CSS stay intact.
- **XSS / injection risk:** Rich text increases attack surface. Mitigation: never store or render untrusted client HTML; parse/validate strictly on an allowlist into a typed JSON AST and render exclusively through escaped template/helper output with CSS classes (no inline `style` attributes).
- **Schema migration safety:** Existing installations hold durable SQLite data. Mitigation: additive `ALTER TABLE cards ADD COLUMN ...` migration from v3 to v4 inside `BEGIN IMMEDIATE` transaction, covered by automated migration tests.
- **Coordination with #4 and #5:** #4 (public sharing) and #5 (JSON import/export) remain open; keeping a shared card-face rendering macro and nullable `*_rich` columns ensures clean forward compatibility.

## Progress log

- 2026-11-27: Read `AGENTS.md`, `PLAN.md`, `README.md`, `docs/architecture.md`, `docs/technical-decisions.md`, source modules, templates, static JS/CSS, and existing tests. Inspected GitHub Issue #7 and repository state on branch `arena/d38a9b9c-virtual-index-card` (clean working tree at `732bbee`). Updated `PLAN.md` with the Issue #7 plan and open design questions for user approval.
- 2026-11-27: User approved the plan and proposed resolutions. Bootstrapped `uv` in `/tmp/uv-env`, ran `uv sync --group dev`, and verified the baseline suite (74 passed).
- 2026-11-27: Implemented `formatting.py` (allowlisted rich-text AST canonicalization, Unicode code-point visible length validation, WCAG AA 6-color palette, and MarkupSafe rendering), updated `domain.py`, added schema v4 (`front_rich`, `back_rich`) and `v3 -> v4` migration in `db.py` and `repository.py`, updated `app.py` and templates (`_card_components.html`, `base.html`, `deck.html`, `review.html`), and built the accessible rich-text editor toolbar and styling in `static/app.js` and `static/styles.css`.
- 2026-11-27: Added unit, contrast, repository, migration, API/XSS/isolation, and toolbar accessibility tests. Updated `README.md`, `docs/architecture.md`, and `docs/technical-decisions.md` (`TD-015`). Verified `uv run pytest -q` (90 passed, 1 existing Starlette/httpx deprecation warning), `python -m compileall -q src tests`, `node --check src/virtual_index_card/static/app.js`, pure JS formatting logic checks via Node, and `git diff --check`. Live browser DOM `contenteditable` typing/selection behavior was not run in a headless browser (no Chromium/Playwright installed in sandbox).
- 2026-11-27: Removed the block-quote toolbar button and editor `blockquote` toggle per user request (`_card_components.html`, `static/app.js`, `tests/test_app.py`, and docs), while preserving safe backend/CSS handling for any existing `blockquote` records. Re-ran full validation suite.
- 2026-11-27: Removed `orange` and `pink` text color options per user request (`formatting.py`, `static/app.js`, `static/styles.css`, tests, and docs), leaving the 4-color accessible palette (`black`, `green`, `red`, `blue`). Re-ran full validation suite.
