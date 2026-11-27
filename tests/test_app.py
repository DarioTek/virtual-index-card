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


def test_duplicate_request_is_rejected(client: TestClient) -> None:
    register(client, "alice")
    response = client.post(
        "/register",
        data={"username": "ALICE"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "already taken" in response.text


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
    second_id = client.post(
        "/api/cards", json={"front": "second", "back": "two"}, headers=headers
    ).json()["card"]["id"]

    updated = client.patch(
        f"/api/cards/{card_id}",
        json={"front": "edited", "back": "one"},
        headers=headers,
    )
    assert updated.json()["card"]["front"] == "edited"

    reloaded = client.get("/")
    assert "edited" in reloaded.text
    assert "second" in reloaded.text
    assert [
        int(value) for value in re.findall(r'data-card-id="(\d+)"', reloaded.text)
    ] == [second_id, card_id]
    assert 'id="shuffle-btn"' not in reloaded.text

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

    assert client.post("/api/deck/shuffle").status_code == 403
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
    assert rendered_ids == [4, 3, 2, 1]
    assert 'id="shuffle-btn"' not in page

    for index, card in enumerate(order):
        review = fresh_client.get(f"/review?index={index}")
        assert [
            int(value) for value in re.findall(r'data-card-id="(\d+)"', review.text)
        ] == [card["id"]]
        assert 'id="shuffle-btn"' in review.text
        assert f"Card {index + 1} of 4" in review.text

    new_id = add_card(fresh_client, "card 4", "back 4")
    assert [
        int(value) for value in re.findall(r'data-card-id="(\d+)"', fresh_client.get("/").text)
    ] == [new_id, 4, 3, 2, 1]
    assert [
        int(value)
        for value in re.findall(r'data-card-id="(\d+)"', fresh_client.get("/review?index=4").text)
    ] == [new_id]


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


def add_card(client: TestClient, front: str, back: str) -> int:
    response = client.post(
        "/api/cards",
        json={"front": front, "back": back},
        headers=csrf_headers(client),
    )
    assert response.status_code == 201
    return response.json()["card"]["id"]


def test_review_requires_authentication(client: TestClient) -> None:
    response = client.get("/review", follow_redirects=False)
    assert response.headers["location"] == "/login"


def test_review_shows_one_card_and_cycles(client: TestClient) -> None:
    register(client, "alice")
    ids = [add_card(client, f"front {index}", f"back {index}") for index in range(3)]

    page = client.get("/review")
    assert page.status_code == 200
    assert "Card 1 of 3" in page.text
    assert [int(value) for value in re.findall(r'data-card-id="(\d+)"', page.text)] == [ids[0]]
    assert 'aria-pressed="false"' in page.text
    assert 'id="shuffle-btn"' in page.text
    assert 'id="shuffle-btn" class="secondary" disabled' not in page.text
    assert "front 0" in page.text
    assert "back 0" in page.text

    second = client.get("/review?index=1")
    assert "Card 2 of 3" in second.text
    assert [int(value) for value in re.findall(r'data-card-id="(\d+)"', second.text)] == [ids[1]]

    wrap_forward = client.get("/review?index=3")
    assert "Card 1 of 3" in wrap_forward.text

    wrap_backward = client.get("/review?index=-1")
    assert "Card 3 of 3" in wrap_backward.text


def test_review_empty_deck_shows_empty_state(client: TestClient) -> None:
    register(client, "alice")
    page = client.get("/review")
    assert page.status_code == 200
    assert "No cards to review" in page.text
    assert "Add some cards to your deck" in page.text
    assert 'id="shuffle-btn"' not in page.text

    add_card(client, "only card", "back")
    single = client.get("/review")
    assert 'id="shuffle-btn" class="secondary" disabled' in single.text


def test_review_shows_only_the_signed_in_accounts_cards(
    settings: Settings, client: TestClient
) -> None:
    register(client, "alice")
    add_card(client, "alice front", "alice back")

    other = TestClient(create_app(settings))
    register(other, "bob")
    add_card(other, "bob front", "bob back")

    page = other.get("/review")
    assert "bob front" in page.text
    assert "alice front" not in page.text
    assert "Card 1 of 1" in page.text
