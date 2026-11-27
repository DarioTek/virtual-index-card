"""Framework-independent card model and deck behavior."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Sequence

MAX_NOTE_LENGTH = 5000
USERNAME_MIN = 3
USERNAME_MAX = 30
PASSWORD_MIN = 8
PASSWORD_MAX = 128


def validate_username(username: str) -> str | None:
    if not (USERNAME_MIN <= len(username) <= USERNAME_MAX):
        return f"Username must be between {USERNAME_MIN} and {USERNAME_MAX} characters."
    if not username.replace("_", "").replace("-", "").isalnum():
        return "Use only letters, numbers, underscores, or hyphens in usernames."
    return None


def validate_password(password: str) -> str | None:
    if len(password) < PASSWORD_MIN:
        return f"Password must be at least {PASSWORD_MIN} characters."
    if len(password) > PASSWORD_MAX:
        return f"Password must be at most {PASSWORD_MAX} characters."
    return None


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
