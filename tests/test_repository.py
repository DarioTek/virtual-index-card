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


def test_decks_are_account_scoped_and_cards_are_independent(
    connection: sqlite3.Connection,
) -> None:
    alice = add_user(connection, "alice")
    bob = add_user(connection, "bob")
    alice_decks = repo.list_decks(connection, alice)
    bob_decks = repo.list_decks(connection, bob)
    assert [deck["name"] for deck in alice_decks] == ["My Deck 1"]
    assert [deck["name"] for deck in bob_decks] == ["My Deck 1"]

    second = repo.create_deck(connection, alice, utc_now())
    third = repo.create_deck(connection, alice, utc_now())
    assert [deck["name"] for deck in repo.list_decks(connection, alice)] == [
        "My Deck 1", "My Deck 2", "My Deck 3"
    ]
    assert repo.get_deck(connection, bob, int(second["id"])) is None

    first_card = repo.create_card(connection, alice, "first", "one", utc_now())
    second_card = repo.create_card(
        connection, alice, "second", "two", utc_now(), int(second["id"])
    )
    assert [card.front for card in repo.list_cards(connection, alice)] == ["first"]
    assert [card.front for card in repo.list_cards(connection, alice, int(second["id"]))] == ["second"]
    assert repo.get_card(connection, alice, first_card.id, int(second["id"])) is None
    assert repo.update_card(
        connection, alice, second_card.id, "wrong deck", "no", utc_now(), int(third["id"])
    ) is None
    assert repo.delete_card(connection, alice, second_card.id, int(third["id"])) is False
    assert repo.list_cards(connection, bob) == []


def test_custom_deck_names_and_rename_are_account_scoped(
    connection: sqlite3.Connection,
) -> None:
    alice = add_user(connection, "alice")
    bob = add_user(connection, "bob")
    biology = repo.create_deck(connection, alice, utc_now(), "Biology")
    bob_biology = repo.create_deck(connection, bob, utc_now(), "biology")
    card = repo.create_card(
        connection, alice, "cell", "membrane", utc_now(), int(biology["id"])
    )

    with pytest.raises(repo.DeckNameTaken):
        repo.create_deck(connection, alice, utc_now(), "BIOLOGY")

    renamed = repo.rename_deck(
        connection, alice, int(biology["id"]), "Life Sciences"
    )
    assert renamed is not None and renamed["name"] == "Life Sciences"
    assert repo.get_deck(connection, bob, int(biology["id"])) is None
    assert repo.rename_deck(connection, bob, int(biology["id"]), "Stolen") is None
    assert repo.get_deck(connection, bob, int(bob_biology["id"]))["name"] == "biology"
    preserved = repo.list_cards(connection, alice, int(biology["id"]))
    assert [item.id for item in preserved] == [card.id]
    assert [item.position for item in preserved] == [0]


def test_generated_deck_names_advance_past_custom_numeric_names(
    connection: sqlite3.Connection,
) -> None:
    alice = add_user(connection, "alice")
    repo.create_deck(connection, alice, utc_now(), "My Deck 7")
    generated = repo.create_deck(connection, alice, utc_now())
    assert generated["name"] == "My Deck 8"


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
