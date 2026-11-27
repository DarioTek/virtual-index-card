"""SQLite connection handling, schema creation, and migrations."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Sequence

SCHEMA_VERSION = 3

SCHEMA_STATEMENTS: Sequence[str] = (
    """
    CREATE TABLE users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
        salt          TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role          TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
        created_at    TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE decks (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name       TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (user_id, name COLLATE NOCASE),
        UNIQUE (id, user_id)
    )
    """,
    "CREATE INDEX idx_decks_user ON decks(user_id, id)",
    """
    CREATE TABLE sessions (
        token_hash TEXT PRIMARY KEY,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        expires_at INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX idx_sessions_expiry ON sessions(expires_at)",
    """
    CREATE TABLE cards (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        deck_id    INTEGER NOT NULL,
        front      TEXT NOT NULL,
        back       TEXT NOT NULL,
        position   INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (deck_id, user_id) REFERENCES decks(id, user_id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX idx_cards_user_position ON cards(user_id, position)",
    "CREATE INDEX idx_cards_deck_position ON cards(deck_id, position)",
    """
    CREATE TABLE account_requests (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        username        TEXT NOT NULL,
        contact         TEXT,
        note            TEXT,
        status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected')),
        created_at      TEXT NOT NULL,
        decided_at      TEXT,
        decided_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    "CREATE INDEX idx_account_requests_status ON account_requests(status, id)",
)

# Additive migration from schema version 1 (users without role, no account_requests).
# Existing accounts become plain users; administrators are created out of band via
# the create_admin CLI or the VIC_ADMIN_* environment variables.
MIGRATION_1_TO_2: Sequence[str] = (
    "ALTER TABLE users "
    "ADD COLUMN role TEXT NOT NULL DEFAULT 'user' "
    "CHECK (role IN ('admin', 'user'))",
    """
    CREATE TABLE account_requests (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        username        TEXT NOT NULL,
        contact         TEXT,
        note            TEXT,
        status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected')),
        created_at      TEXT NOT NULL,
        decided_at      TEXT,
        decided_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    "CREATE INDEX idx_account_requests_status ON account_requests(status, id)",
)

MIGRATION_2_TO_3: Sequence[str] = (
    """
    CREATE TABLE decks (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name       TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (user_id, name COLLATE NOCASE),
        UNIQUE (id, user_id)
    )
    """,
    "CREATE INDEX idx_decks_user ON decks(user_id, id)",
    """
    INSERT INTO decks (user_id, name, created_at)
    SELECT id, 'My Deck 1', created_at FROM users ORDER BY id
    """,
    """
    CREATE TABLE cards_v3 (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        deck_id    INTEGER NOT NULL,
        front      TEXT NOT NULL,
        back       TEXT NOT NULL,
        position   INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (deck_id, user_id) REFERENCES decks(id, user_id) ON DELETE CASCADE
    )
    """,
    """
    INSERT INTO cards_v3 (id, user_id, deck_id, front, back, position, created_at, updated_at)
    SELECT c.id, c.user_id, d.id, c.front, c.back, c.position, c.created_at, c.updated_at
    FROM cards c JOIN decks d ON d.user_id = c.user_id
    """,
    "DROP TABLE cards",
    "ALTER TABLE cards_v3 RENAME TO cards",
    "CREATE INDEX idx_cards_user_position ON cards(user_id, position)",
    "CREATE INDEX idx_cards_deck_position ON cards(deck_id, position)",
)


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(path: Path) -> None:
    """Create the schema once, or upgrade an older database in place."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                for statement in SCHEMA_STATEMENTS:
                    connection.execute(statement)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            elif version == 1:
                for statement in MIGRATION_1_TO_2:
                    connection.execute(statement)
                for statement in MIGRATION_2_TO_3:
                    connection.execute(statement)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            elif version == 2:
                for statement in MIGRATION_2_TO_3:
                    connection.execute(statement)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            elif version != SCHEMA_VERSION:
                raise RuntimeError(
                    f"Unsupported database schema version {version}; "
                    f"expected {SCHEMA_VERSION}."
                )
