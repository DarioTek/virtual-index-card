"""SQLite queries. Every card query is scoped to an account."""

from __future__ import annotations

import sqlite3
from typing import Sequence

from .domain import Card
from .security import hash_token  # noqa: F401  (kept for API symmetry in tests)


class UsernameTaken(Exception):
    """Raised when a registration username already exists."""


def _to_card(row: sqlite3.Row) -> Card:
    return Card(
        id=row["id"],
        front=row["front"],
        back=row["back"],
        position=row["position"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# --- Users -----------------------------------------------------------------

def create_user(
    connection: sqlite3.Connection,
    username: str,
    salt_hex: str,
    password_hash_hex: str,
    created_at: str,
) -> int:
    try:
        cursor = connection.execute(
            "INSERT INTO users (username, salt, password_hash, created_at) "
            "VALUES (?, ?, ?, ?)",
            (username, salt_hex, password_hash_hex, created_at),
        )
    except sqlite3.IntegrityError as exc:
        raise UsernameTaken(f"Username {username!r} is already registered.") from exc
    return int(cursor.lastrowid)


def get_user_by_username(connection: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
    ).fetchone()


def get_user_by_id(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


# --- Sessions --------------------------------------------------------------

def create_session(
    connection: sqlite3.Connection,
    token: str,
    user_id: int,
    expires_at: int,
    created_at: str,
) -> None:
    connection.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at, created_at) "
        "VALUES (?, ?, ?, ?)",
        (hash_token(token), user_id, expires_at, created_at),
    )


def get_session_user(
    connection: sqlite3.Connection, token: str, now: int
) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.token_hash = ? AND s.expires_at > ?",
        (hash_token(token), now),
    ).fetchone()


def delete_session(connection: sqlite3.Connection, token: str) -> None:
    connection.execute(
        "DELETE FROM sessions WHERE token_hash = ?", (hash_token(token),)
    )


def delete_expired_sessions(connection: sqlite3.Connection, now: int) -> None:
    connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))


# --- Cards -----------------------------------------------------------------

def list_cards(connection: sqlite3.Connection, user_id: int) -> list[Card]:
    """Return the persisted order used during Review."""
    rows = connection.execute(
        "SELECT * FROM cards WHERE user_id = ? ORDER BY position, id", (user_id,)
    ).fetchall()
    return [_to_card(row) for row in rows]


def list_cards_newest_first(connection: sqlite3.Connection, user_id: int) -> list[Card]:
    """Return creation order for managing cards, independent of Review order."""
    rows = connection.execute(
        "SELECT * FROM cards WHERE user_id = ? ORDER BY created_at DESC, id DESC",
        (user_id,),
    ).fetchall()
    return [_to_card(row) for row in rows]


def get_card(
    connection: sqlite3.Connection, user_id: int, card_id: int
) -> Card | None:
    row = connection.execute(
        "SELECT * FROM cards WHERE user_id = ? AND id = ?", (user_id, card_id)
    ).fetchone()
    return _to_card(row) if row else None


def create_card(
    connection: sqlite3.Connection,
    user_id: int,
    front: str,
    back: str,
    created_at: str,
) -> Card:
    cursor = connection.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS next_position FROM cards "
        "WHERE user_id = ?",
        (user_id,),
    )
    position = int(cursor.fetchone()["next_position"])
    insert = connection.execute(
        "INSERT INTO cards (user_id, front, back, position, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, front, back, position, created_at, created_at),
    )
    card = get_card(connection, user_id, int(insert.lastrowid))
    assert card is not None
    return card


def update_card(
    connection: sqlite3.Connection,
    user_id: int,
    card_id: int,
    front: str,
    back: str,
    updated_at: str,
) -> Card | None:
    cursor = connection.execute(
        "UPDATE cards SET front = ?, back = ?, updated_at = ? "
        "WHERE user_id = ? AND id = ?",
        (front, back, updated_at, user_id, card_id),
    )
    if cursor.rowcount == 0:
        return None
    return get_card(connection, user_id, card_id)


def delete_card(connection: sqlite3.Connection, user_id: int, card_id: int) -> bool:
    cursor = connection.execute(
        "DELETE FROM cards WHERE user_id = ? AND id = ?", (user_id, card_id)
    )
    return cursor.rowcount > 0


def replace_positions(
    connection: sqlite3.Connection, user_id: int, cards: Sequence[Card]
) -> None:
    connection.executemany(
        "UPDATE cards SET position = ? WHERE user_id = ? AND id = ?",
        [(card.position, user_id, card.id) for card in cards],
    )
