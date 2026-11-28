"""Framework-independent card model and deck behavior."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Sequence

from .formatting import (
    MAX_NOTE_LENGTH,
    FormattingValidationError,
    normalize_rich_document,
)

MAX_DECK_NAME_LENGTH = 100
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
    front_rich: dict[str, Any] | None = None
    back_rich: dict[str, Any] | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_note(value: str, field: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise ValidationError(f"{field} must not be empty.")
    if len(text) > MAX_NOTE_LENGTH:
        raise ValidationError(f"{field} must be at most {MAX_NOTE_LENGTH} characters.")
    return text


def clean_card_side(
    plain_value: str,
    rich_value: dict[str, Any] | None,
    field: str,
) -> tuple[str, dict[str, Any] | None]:
    """Validate either a plain-text side or a formatted rich-text side."""
    if rich_value is None:
        return clean_note(plain_value, field), None
    try:
        return normalize_rich_document(rich_value, field, max_length=MAX_NOTE_LENGTH)
    except FormattingValidationError as exc:
        raise ValidationError(str(exc)) from exc


def clean_deck_name(value: str) -> str:
    """Return a trimmed, valid deck name."""
    name = value.strip()
    if not name:
        raise ValidationError("Deck name must not be empty.")
    if len(name) > MAX_DECK_NAME_LENGTH:
        raise ValidationError(
            f"Deck name must be at most {MAX_DECK_NAME_LENGTH} characters."
        )
    return name


def shuffled_cards(cards: Sequence[Card], rng: random.Random | None = None) -> list[Card]:
    """Return a Fisher-Yates shuffle with positions reassigned from zero."""
    result = list(cards)
    generator = rng or random.SystemRandom()
    for index in range(len(result) - 1, 0, -1):
        swap_index = generator.randint(0, index)
        result[index], result[swap_index] = result[swap_index], result[index]
    return [replace(card, position=position) for position, card in enumerate(result)]
