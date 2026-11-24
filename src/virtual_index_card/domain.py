"""Framework-independent card model and deck behavior."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Sequence

MAX_NOTE_LENGTH = 5000


class ValidationError(ValueError):
    """Raised when note input cannot be stored."""


@dataclass(frozen=True)
class Card:
    id: int
    front: str
    back: str
    position: int
    created_at: str
    updated_at: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_note(value: str, field: str) -> str:
    text = value.strip()
    if not text:
        raise ValidationError(f"{field} must not be empty.")
    if len(text) > MAX_NOTE_LENGTH:
        raise ValidationError(f"{field} must be at most {MAX_NOTE_LENGTH} characters.")
    return text


def shuffled_cards(cards: Sequence[Card], rng: random.Random | None = None) -> list[Card]:
    """Return a Fisher-Yates shuffle with positions reassigned from zero."""
    result = list(cards)
    generator = rng or random.SystemRandom()
    for index in range(len(result) - 1, 0, -1):
        swap_index = generator.randint(0, index)
        result[index], result[swap_index] = result[swap_index], result[index]
    return [replace(card, position=position) for position, card in enumerate(result)]
