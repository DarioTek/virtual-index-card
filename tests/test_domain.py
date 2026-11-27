import random

import pytest

from virtual_index_card.domain import (
    Card,
    ValidationError,
    clean_deck_name,
    clean_note,
    shuffled_cards,
)


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
