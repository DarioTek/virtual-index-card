"""Rich-text flash-card formatting model, validation, and safe HTML rendering."""

from __future__ import annotations

import json
from typing import Any

from markupsafe import Markup, escape

RICH_FORMAT_VERSION = 1
MAX_NOTE_LENGTH = 5000
MAX_BLOCKS = 20000
MAX_RUNS_PER_BLOCK = 5000

# WCAG AA (>= 4.5:1) accessible shades on both card front (#fffefa) and back (#edf8f6).
PALETTE_COLORS: dict[str, str] = {
    "black": "#172033",
    "green": "#066e42",
    "red": "#b42318",
    "blue": "#175cd3",
}

BLOCK_TYPES = ("paragraph", "blockquote")
_ALLOWED_DOC_KEYS = {"version", "blocks"}
_ALLOWED_BLOCK_KEYS = {"type", "runs"}
_ALLOWED_RUN_KEYS = {"text", "bold", "italic", "underline", "color"}


class FormattingValidationError(ValueError):
    """Raised when rich-text formatting payload is invalid."""


def _canonical_run(
    text: str,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    color: str | None = None,
) -> dict[str, Any]:
    run: dict[str, Any] = {"text": text}
    if bold:
        run["bold"] = True
    if italic:
        run["italic"] = True
    if underline:
        run["underline"] = True
    if color is not None:
        run["color"] = color
    return run


def _run_style_key(run: dict[str, Any]) -> tuple[bool, bool, bool, str | None]:
    return (
        bool(run.get("bold", False)),
        bool(run.get("italic", False)),
        bool(run.get("underline", False)),
        run.get("color"),
    )


def _trim_blocks_whitespace(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Trim leading and trailing whitespace across blocks while keeping internal newlines."""
    trimmed = [
        {"type": block["type"], "runs": [dict(run) for run in block["runs"]]}
        for block in blocks
    ]

    while trimmed:
        runs = trimmed[0]["runs"]
        while runs:
            new_text = runs[0]["text"].lstrip()
            if new_text:
                runs[0]["text"] = new_text
                break
            runs.pop(0)
        if runs:
            break
        trimmed.pop(0)

    while trimmed:
        runs = trimmed[-1]["runs"]
        while runs:
            new_text = runs[-1]["text"].rstrip()
            if new_text:
                runs[-1]["text"] = new_text
                break
            runs.pop()
        if runs:
            break
        trimmed.pop()

    return trimmed


def normalize_rich_document(
    raw_doc: Any,
    field: str,
    max_length: int = MAX_NOTE_LENGTH,
) -> tuple[str, dict[str, Any] | None]:
    """Validate and canonicalize a rich-text document.

    Returns ``(plain_visible_text, canonical_doc_or_none)``.
    If the document contains no block quotes and no inline styles, ``None`` is
    returned as the canonical rich document so plain cards stay plain text.
    """
    if not isinstance(raw_doc, dict):
        raise FormattingValidationError(f"{field} formatting must be an object.")
    if not set(raw_doc.keys()).issubset(_ALLOWED_DOC_KEYS):
        raise FormattingValidationError(f"{field} formatting contains unsupported fields.")
    if raw_doc.get("version") != RICH_FORMAT_VERSION:
        raise FormattingValidationError(f"{field} formatting version is unsupported.")

    raw_blocks = raw_doc.get("blocks")
    if not isinstance(raw_blocks, list) or not raw_blocks:
        raise FormattingValidationError(f"{field} formatting must contain blocks.")
    if len(raw_blocks) > MAX_BLOCKS:
        raise FormattingValidationError(f"{field} contains too many blocks.")

    expanded_blocks: list[dict[str, Any]] = []
    for raw_block in raw_blocks:
        if not isinstance(raw_block, dict):
            raise FormattingValidationError(f"{field} block must be an object.")
        if not set(raw_block.keys()).issubset(_ALLOWED_BLOCK_KEYS):
            raise FormattingValidationError(f"{field} block contains unsupported fields.")
        block_type = raw_block.get("type")
        if block_type not in BLOCK_TYPES:
            raise FormattingValidationError(f"{field} block type is invalid.")
        raw_runs = raw_block.get("runs")
        if not isinstance(raw_runs, list):
            raise FormattingValidationError(f"{field} block runs must be a list.")
        if len(raw_runs) > MAX_RUNS_PER_BLOCK:
            raise FormattingValidationError(f"{field} block contains too many runs.")

        current_runs: list[dict[str, Any]] = []
        for raw_run in raw_runs:
            if not isinstance(raw_run, dict):
                raise FormattingValidationError(f"{field} run must be an object.")
            if not set(raw_run.keys()).issubset(_ALLOWED_RUN_KEYS):
                raise FormattingValidationError(f"{field} run contains unsupported fields.")

            text = raw_run.get("text")
            if not isinstance(text, str):
                raise FormattingValidationError(f"{field} run text must be a string.")

            bold = raw_run.get("bold", False)
            italic = raw_run.get("italic", False)
            underline = raw_run.get("underline", False)
            if not (
                isinstance(bold, bool)
                and isinstance(italic, bool)
                and isinstance(underline, bool)
            ):
                raise FormattingValidationError(f"{field} run styles must be booleans.")

            color = raw_run.get("color", None)
            if color is not None and (not isinstance(color, str) or color not in PALETTE_COLORS):
                raise FormattingValidationError(f"{field} text color is invalid.")

            normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
            if not normalized_text:
                continue

            parts = normalized_text.split("\n")
            for index, part in enumerate(parts):
                if index > 0:
                    expanded_blocks.append({"type": block_type, "runs": current_runs})
                    current_runs = []
                    if len(expanded_blocks) > MAX_BLOCKS:
                        raise FormattingValidationError(f"{field} contains too many lines.")
                if part:
                    current_runs.append(
                        _canonical_run(
                            part,
                            bold=bold,
                            italic=italic,
                            underline=underline,
                            color=color,
                        )
                    )

        expanded_blocks.append({"type": block_type, "runs": current_runs})
        if len(expanded_blocks) > MAX_BLOCKS:
            raise FormattingValidationError(f"{field} contains too many lines.")

    trimmed_blocks = _trim_blocks_whitespace(expanded_blocks)
    if not trimmed_blocks:
        raise FormattingValidationError(f"{field} must not be empty.")

    canonical_blocks: list[dict[str, Any]] = []
    for block in trimmed_blocks:
        merged_runs: list[dict[str, Any]] = []
        for run in block["runs"]:
            if not run["text"]:
                continue
            if merged_runs and _run_style_key(merged_runs[-1]) == _run_style_key(run):
                merged_runs[-1]["text"] += run["text"]
            else:
                merged_runs.append(
                    _canonical_run(
                        run["text"],
                        bold=bool(run.get("bold", False)),
                        italic=bool(run.get("italic", False)),
                        underline=bool(run.get("underline", False)),
                        color=run.get("color"),
                    )
                )
        canonical_blocks.append({"type": block["type"], "runs": merged_runs})

    plain_text = "\n".join(
        "".join(run["text"] for run in block["runs"]) for block in canonical_blocks
    )
    if not plain_text.strip():
        raise FormattingValidationError(f"{field} must not be empty.")
    if len(plain_text) > max_length:
        raise FormattingValidationError(
            f"{field} must be at most {max_length} characters."
        )

    has_formatting = any(
        block["type"] != "paragraph"
        or any(
            run.get("bold")
            or run.get("italic")
            or run.get("underline")
            or run.get("color") is not None
            for run in block["runs"]
        )
        for block in canonical_blocks
    )
    if not has_formatting:
        return plain_text, None

    return plain_text, {"version": RICH_FORMAT_VERSION, "blocks": canonical_blocks}


def serialize_rich_document(doc: dict[str, Any] | None) -> str | None:
    if doc is None:
        return None
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":"))


def deserialize_rich_document(raw: str | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    return json.loads(raw)


def _render_runs(runs: list[dict[str, Any]]) -> Markup:
    if not runs:
        return Markup("<br>")
    parts: list[Markup] = []
    for run in runs:
        node: Markup | str = escape(run["text"])
        if run.get("underline"):
            node = Markup("<u>{}</u>").format(node)
        if run.get("italic"):
            node = Markup("<em>{}</em>").format(node)
        if run.get("bold"):
            node = Markup("<strong>{}</strong>").format(node)
        color = run.get("color")
        if color in PALETTE_COLORS:
            node = Markup('<span class="fmt-color-{}">{}</span>').format(color, node)
        parts.append(Markup(node))
    return Markup("").join(parts)


def render_card_face(text: str, rich_doc: dict[str, Any] | None = None) -> Markup:
    """Render a card face as safe HTML phrasing markup using CSS classes."""
    if rich_doc is None:
        return Markup('<span class="card-rich-content card-face-plain">{}</span>').format(text)

    blocks = rich_doc.get("blocks", [])
    rendered_blocks: list[Markup] = []
    index = 0
    while index < len(blocks):
        block = blocks[index]
        if block.get("type") == "blockquote":
            quote_lines: list[Markup] = []
            while index < len(blocks) and blocks[index].get("type") == "blockquote":
                line_html = _render_runs(blocks[index].get("runs", []))
                quote_lines.append(
                    Markup('<span class="fmt-quote-line">{}</span>').format(line_html)
                )
                index += 1
            rendered_blocks.append(
                Markup('<span class="fmt-block fmt-quote" role="blockquote">{}</span>').format(
                    Markup("").join(quote_lines)
                )
            )
        else:
            line_html = _render_runs(block.get("runs", []))
            rendered_blocks.append(
                Markup('<span class="fmt-block fmt-paragraph">{}</span>').format(line_html)
            )
            index += 1

    return Markup('<span class="card-rich-content">{}</span>').format(
        Markup("").join(rendered_blocks)
    )
