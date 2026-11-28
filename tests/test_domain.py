import random

import pytest

from virtual_index_card.domain import (
    Card,
    ValidationError,
    clean_card_side,
    clean_deck_name,
    clean_note,
    shuffled_cards,
)
from virtual_index_card.formatting import PALETTE_COLORS, render_card_face


def make_card(card_id: int, position: int) -> Card:
    return Card(
        id=card_id,
        front=f"front {card_id}",
        back=f"back {card_id}",
        position=position,
        created_at="2026-11-24T00:00:00+00:00",
        updated_at="2026-11-24T00:00:00+00:00",
    )


def test_shuffle_preserves_cards_and_reassigns_positions() -> None:
    cards = [make_card(1, 0), make_card(2, 1), make_card(3, 2), make_card(4, 3)]
    result = shuffled_cards(cards, rng=random.Random(7))

    assert sorted(card.id for card in result) == [1, 2, 3, 4]
    assert [card.position for card in result] == [0, 1, 2, 3]
    assert len({card.id for card in result}) == len(cards)


def test_shuffle_is_deterministic_with_injected_rng() -> None:
    cards = [make_card(index, index) for index in range(10)]
    first = shuffled_cards(cards, rng=random.Random(42))
    second = shuffled_cards(cards, rng=random.Random(42))

    assert [card.id for card in first] == [card.id for card in second]


def test_shuffle_handles_empty_and_single_card_decks() -> None:
    assert shuffled_cards([], rng=random.Random(1)) == []
    single = [make_card(9, 0)]
    assert [card.id for card in shuffled_cards(single, rng=random.Random(1))] == [9]


def test_clean_note_trims_and_validates() -> None:
    assert clean_note("  hello  ", "Front") == "hello"
    with pytest.raises(ValidationError):
        clean_note("   ", "Front")
    with pytest.raises(ValidationError):
        clean_note("x" * 5001, "Back")


def test_clean_deck_name_trims_and_validates_boundaries() -> None:
    assert clean_deck_name("  Biology  ") == "Biology"
    assert clean_deck_name("x" * 100) == "x" * 100
    with pytest.raises(ValidationError, match="must not be empty"):
        clean_deck_name("   ")
    with pytest.raises(ValidationError, match="at most 100"):
        clean_deck_name("x" * 101)


def _wcag_contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    def linearize(channel: int) -> float:
        c = channel / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    def luminance(hex_color: str) -> float:
        raw = hex_color.lstrip("#")
        r, g, b = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
        return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)

    l1, l2 = luminance(fg_hex), luminance(bg_hex)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def test_palette_has_expected_colors_and_meets_wcag_aa_contrast() -> None:
    assert set(PALETTE_COLORS.keys()) == {"black", "green", "red", "orange", "blue", "pink"}
    card_backgrounds = ("#fffefa", "#edf8f6", "#f9fffd", "#f3f6f9")
    for name, fg_hex in PALETTE_COLORS.items():
        for bg_hex in card_backgrounds:
            assert _wcag_contrast_ratio(fg_hex, bg_hex) >= 4.5, (
                f"{name} ({fg_hex}) failed contrast on {bg_hex}"
            )


def test_rich_formatting_canonicalizes_overlapping_styles_and_multiline_quotes() -> None:
    doc = {
        "version": 1,
        "blocks": [
            {
                "type": "paragraph",
                "runs": [
                    {"text": "  Hello ", "bold": True},
                    {"text": "world", "bold": True, "italic": True, "underline": True, "color": "blue"},
                ],
            },
            {
                "type": "blockquote",
                "runs": [
                    {"text": "Line 1\nLine 2  ", "color": "orange", "italic": True},
                ],
            },
        ],
    }
    plain, rich = clean_card_side("", doc, "Front")
    assert plain == "Hello world\nLine 1\nLine 2"
    assert rich == {
        "version": 1,
        "blocks": [
            {
                "type": "paragraph",
                "runs": [
                    {"text": "Hello ", "bold": True},
                    {"text": "world", "bold": True, "italic": True, "underline": True, "color": "blue"},
                ],
            },
            {
                "type": "blockquote",
                "runs": [{"text": "Line 1", "italic": True, "color": "orange"}],
            },
            {
                "type": "blockquote",
                "runs": [{"text": "Line 2", "italic": True, "color": "orange"}],
            },
        ],
    }

    html = str(render_card_face(plain, rich))
    assert "<strong>Hello </strong>" in html
    assert '<span class="fmt-color-blue"><strong><em><u>world</u></em></strong></span>' in html
    assert html.count('<span class="fmt-block fmt-quote" role="blockquote">') == 1
    assert html.count('<span class="fmt-quote-line">') == 2
    assert "style=" not in html


def test_unstyled_rich_document_collapses_to_plain_text() -> None:
    doc = {
        "version": 1,
        "blocks": [{"type": "paragraph", "runs": [{"text": "  plain ", "bold": False}, {"text": "text  "}]}],
    }
    plain, rich = clean_card_side("", doc, "Back")
    assert plain == "plain text"
    assert rich is None


def test_rich_formatting_enforces_5000_unicode_code_point_limit() -> None:
    exact_ascii = {
        "version": 1,
        "blocks": [{"type": "paragraph", "runs": [{"text": "a" * 5000, "bold": True, "color": "red"}]}],
    }
    plain, rich = clean_card_side("", exact_ascii, "Front")
    assert len(plain) == 5000
    assert rich is not None

    over_ascii = {
        "version": 1,
        "blocks": [{"type": "paragraph", "runs": [{"text": "a" * 5001, "bold": True}]}],
    }
    with pytest.raises(ValidationError, match="at most 5000"):
        clean_card_side("", over_ascii, "Front")

    exact_emoji = {
        "version": 1,
        "blocks": [{"type": "blockquote", "runs": [{"text": "😀" * 5000, "italic": True}]}],
    }
    plain_emoji, _ = clean_card_side("", exact_emoji, "Back")
    assert len(plain_emoji) == 5000

    over_emoji = {
        "version": 1,
        "blocks": [{"type": "blockquote", "runs": [{"text": "😀" * 5001, "italic": True}]}],
    }
    with pytest.raises(ValidationError, match="at most 5000"):
        clean_card_side("", over_emoji, "Back")

    empty_formatted = {
        "version": 1,
        "blocks": [{"type": "blockquote", "runs": [{"text": "   \n  ", "bold": True}]}],
    }
    with pytest.raises(ValidationError, match="must not be empty"):
        clean_card_side("", empty_formatted, "Front")


@pytest.mark.parametrize(
    "bad_doc",
    [
        {"version": 2, "blocks": [{"type": "paragraph", "runs": [{"text": "hi"}]}]},
        {"version": 1, "blocks": [], "extra": True},
        {"version": 1, "blocks": [{"type": "script", "runs": [{"text": "alert(1)"}]}]},
        {"version": 1, "blocks": [{"type": "paragraph", "runs": [{"text": "hi", "color": "yellow"}]}]},
        {"version": 1, "blocks": [{"type": "paragraph", "runs": [{"text": "hi", "bold": "yes"}]}]},
        {"version": 1, "blocks": [{"type": "paragraph", "runs": [{"text": "hi", "href": "javascript:alert(1)"}]}]},
    ],
)
def test_invalid_rich_documents_are_rejected(bad_doc: dict) -> None:
    with pytest.raises(ValidationError):
        clean_card_side("", bad_doc, "Front")


def test_plain_and_rich_renderer_escapes_markup_like_text() -> None:
    plain_html = str(render_card_face("<script>alert(1)</script> & <b>tag</b>", None))
    assert "<script>" not in plain_html
    assert "<b>" not in plain_html
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; &lt;b&gt;tag&lt;/b&gt;" in plain_html

    rich_doc = {
        "version": 1,
        "blocks": [{"type": "paragraph", "runs": [{"text": "<img src=x onerror=alert(1)>", "bold": True}]}],
    }
    rich_html = str(render_card_face("<img src=x onerror=alert(1)>", rich_doc))
    assert "<img" not in rich_html
    assert "<strong>&lt;img src=x onerror=alert(1)&gt;</strong>" in rich_html
