import re

from fastapi.testclient import TestClient

from virtual_index_card.app import create_app
from virtual_index_card.config import Settings
from tests.conftest import csrf_headers, register


def test_register_creates_private_deck(client: TestClient, settings: Settings) -> None:
    register(client, "alice")

    assert client.cookies.get("vic_session")
    assert client.cookies.get("vic_csrf")
    page = client.get("/")
    assert page.status_code == 200
    assert "alice" in page.text
    assert "No cards yet" in page.text


def test_duplicate_registration_is_rejected(client: TestClient) -> None:
    register(client, "alice")
    response = client.post(
        "/register",
        data={"username": "ALICE", "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "already registered" in response.text


def test_login_and_logout(client: TestClient) -> None:
    register(client, "alice")
    logout = client.post(
        "/logout",
        data={"csrf_token": client.cookies.get("vic_csrf")},
        follow_redirects=False,
    )
    assert logout.status_code == 303
    assert client.get("/", follow_redirects=False).headers["location"] == "/login"

    bad_login = client.post(
        "/login",
        data={"username": "alice", "password": "wrong"},
        follow_redirects=False,
    )
    assert bad_login.status_code == 401

    good_login = client.post(
        "/login",
        data={"username": "alice", "password": "correct horse battery"},
        follow_redirects=False,
    )
    assert good_login.status_code == 303
    assert client.get("/").status_code == 200


def test_unauthenticated_access_is_blocked(client: TestClient) -> None:
    assert client.get("/", follow_redirects=False).headers["location"] == "/login"
    assert client.post("/api/cards", json={"front": "a", "back": "b"}).status_code == 401
    assert client.post("/api/deck/shuffle").status_code == 401


def test_csrf_token_is_required_for_writes(client: TestClient) -> None:
    register(client, "alice")
    payload = {"front": "question", "back": "answer"}

    missing = client.post("/api/cards", json=payload)
    assert missing.status_code == 403

    allowed = client.post("/api/cards", json=payload, headers=csrf_headers(client))
    assert allowed.status_code == 201
    assert allowed.json()["card"]["front"] == "question"


def test_card_validation_rejects_empty_notes(client: TestClient) -> None:
    register(client, "alice")
    response = client.post(
        "/api/cards",
        json={"front": "  ", "back": "answer"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 422


def test_crud_and_reload_persistence(client: TestClient) -> None:
    register(client, "alice")
    headers = csrf_headers(client)

    created = client.post(
        "/api/cards", json={"front": "first", "back": "one"}, headers=headers
    )
    card_id = created.json()["card"]["id"]
    client.post("/api/cards", json={"front": "second", "back": "two"}, headers=headers)

    updated = client.patch(
        f"/api/cards/{card_id}",
        json={"front": "edited", "back": "one"},
        headers=headers,
    )
    assert updated.json()["card"]["front"] == "edited"

    reloaded = client.get("/")
    assert "edited" in reloaded.text
    assert "second" in reloaded.text

    assert client.delete(f"/api/cards/{card_id}", headers=headers).status_code == 204
    reloaded = client.get("/")
    assert "edited" not in reloaded.text


def test_shuffle_order_persists_for_the_same_account(
    settings: Settings, client: TestClient
) -> None:
    register(client, "alice")
    headers = csrf_headers(client)
    for index in range(4):
        response = client.post(
            "/api/cards",
            json={"front": f"card {index}", "back": f"back {index}"},
            headers=headers,
        )
        assert response.status_code == 201

    shuffled = client.post("/api/deck/shuffle", headers=headers)
    assert shuffled.status_code == 200
    order = shuffled.json()["cards"]
    assert sorted(card["id"] for card in order) == [1, 2, 3, 4]
    assert [card["position"] for card in order] == [0, 1, 2, 3]

    fresh_client = TestClient(create_app(settings))
    response = fresh_client.post(
        "/login",
        data={"username": "alice", "password": "correct horse battery"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    page = fresh_client.get("/").text
    rendered_ids = [int(value) for value in re.findall(r'data-card-id="(\d+)"', page)]
    assert rendered_ids == [card["id"] for card in order]


def test_accounts_cannot_access_each_others_cards(
    settings: Settings, client: TestClient
) -> None:
    register(client, "alice")
    alice_card = client.post(
        "/api/cards",
        json={"front": "alice secret", "back": "private"},
        headers=csrf_headers(client),
    ).json()["card"]["id"]

    other = TestClient(create_app(settings))
    register(other, "bob")

    assert "alice secret" not in other.get("/").text
    assert other.patch(
        f"/api/cards/{alice_card}",
        json={"front": "stolen", "back": "stolen"},
        headers=csrf_headers(other),
    ).status_code == 404
    assert other.delete(
        f"/api/cards/{alice_card}", headers=csrf_headers(other)
    ).status_code == 404
    assert other.post("/api/deck/shuffle", headers=csrf_headers(other)).json() == {"cards": []}


def test_passwords_are_not_stored_in_plain_text(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice")
    import sqlite3

    connection = sqlite3.connect(settings.database_path)
    row = connection.execute(
        "SELECT salt, password_hash FROM users WHERE username = ?", ("alice",)
    ).fetchone()
    connection.close()

    assert row is not None
    assert "correct horse battery" not in row[0]
    assert "correct horse battery" not in row[1]
