import sqlite3

import pytest

from virtual_index_card import repository as repo
from virtual_index_card.domain import utc_now
from virtual_index_card.security import hash_password, new_token


def add_user(connection: sqlite3.Connection, username: str) -> int:
    salt, digest = hash_password("password123")
    return repo.create_user(connection, username, salt, digest, utc_now())


def test_username_is_unique_case_insensitively(connection: sqlite3.Connection) -> None:
    add_user(connection, "Alice")
    with pytest.raises(repo.UsernameTaken):
        add_user(connection, "alice")


def test_card_crud_is_scoped_to_user(connection: sqlite3.Connection) -> None:
    alice = add_user(connection, "alice")
    bob = add_user(connection, "bob")

    first = repo.create_card(connection, alice, "A front", "A back", utc_now())
    second = repo.create_card(connection, alice, "B front", "B back", utc_now())
    repo.create_card(connection, bob, "Bob front", "Bob back", utc_now())

    assert [card.position for card in repo.list_cards(connection, alice)] == [0, 1]
    assert [card.front for card in repo.list_cards(connection, bob)] == ["Bob front"]
    assert repo.get_card(connection, bob, first.id) is None

    updated = repo.update_card(connection, alice, first.id, "New front", "New back", utc_now())
    assert updated is not None and updated.front == "New front"
    assert repo.update_card(connection, bob, first.id, "No", "No", utc_now()) is None

    assert repo.delete_card(connection, bob, second.id) is False
    assert repo.delete_card(connection, alice, second.id) is True
    assert [card.id for card in repo.list_cards(connection, alice)] == [first.id]


def test_management_order_uses_creation_time_not_review_position_or_edits(
    connection: sqlite3.Connection,
) -> None:
    alice = add_user(connection, "alice")
    bob = add_user(connection, "bob")
    first = repo.create_card(connection, alice, "first", "back", "2026-11-24T10:00:00+00:00")
    second = repo.create_card(
        connection, alice, "second", "back", "2026-11-24T10:00:00+00:00"
    )
    third = repo.create_card(connection, alice, "third", "back", "2026-11-24T11:00:00+00:00")
    repo.create_card(connection, bob, "bob", "back", "2026-11-24T12:00:00+00:00")

    repo.update_card(connection, alice, first.id, "edited", "back", "2026-11-24T13:00:00+00:00")
    repo.replace_positions(
        connection,
        alice,
        [
            type(third)(**{**third.__dict__, "position": 0}),
            type(first)(**{**first.__dict__, "position": 1}),
            type(second)(**{**second.__dict__, "position": 2}),
        ],
    )

    assert [card.id for card in repo.list_cards_newest_first(connection, alice)] == [
        third.id, second.id, first.id
    ]
    assert [card.id for card in repo.list_cards(connection, alice)] == [
        third.id, first.id, second.id
    ]
    assert [card.front for card in repo.list_cards_newest_first(connection, bob)] == ["bob"]


def test_session_expires_and_can_be_deleted(connection: sqlite3.Connection) -> None:
    user_id = add_user(connection, "alice")
    token = new_token()
    repo.create_session(connection, token, user_id, 100, utc_now())

    assert repo.get_session_user(connection, token, 99)["id"] == user_id
    assert repo.get_session_user(connection, token, 101) is None
    assert repo.get_session_user(connection, new_token(), 99) is None

    repo.delete_session(connection, token)
    assert repo.get_session_user(connection, token, 99) is None


def test_replace_positions_persists_new_order(connection: sqlite3.Connection) -> None:
    user_id = add_user(connection, "alice")
    first = repo.create_card(connection, user_id, "1", "1", utc_now())
    second = repo.create_card(connection, user_id, "2", "2", utc_now())

    repo.replace_positions(
        connection,
        user_id,
        [
            type(second)(**{**second.__dict__, "position": 0}),
            type(first)(**{**first.__dict__, "position": 1}),
        ],
    )

    assert [card.id for card in repo.list_cards(connection, user_id)] == [second.id, first.id]
