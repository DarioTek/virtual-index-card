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
    assert "My Deck 1" in page.text
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


def test_users_can_create_and_select_independent_decks(client: TestClient) -> None:
    register(client, "alice")
    first_page = client.get("/")
    assert "My Deck 1" in first_page.text
    first_card = add_card(client, "first-deck card", "first answer")
    missing_csrf = client.post("/decks", data={}, follow_redirects=False)
    assert missing_csrf.status_code == 403

    created = client.post(
        "/decks",
        data={"csrf_token": client.cookies.get("vic_csrf")},
        follow_redirects=False,
    )
    assert created.status_code == 303
    assert "deck_id=" in created.headers["location"]
    second_deck_id = int(created.headers["location"].split("deck_id=")[1])
    second_page = client.get(created.headers["location"])
    assert "My Deck 2" in second_page.text
    assert f'id="create-form" class="card-form" data-deck-id="{second_deck_id}"' in second_page.text
    assert "app.js?v=formatting-1" in second_page.text
    assert "first-deck card" not in second_page.text
    second_card_response = client.post(
        f"/api/cards?deck_id={second_deck_id}",
        json={"front": "second-deck card", "back": "second answer"},
        headers=csrf_headers(client),
    )
    assert second_card_response.status_code == 201
    second_card_id = second_card_response.json()["card"]["id"]
    third_card_response = client.post(
        f"/api/cards?deck_id={second_deck_id}",
        json={"front": "another second-deck card", "back": "another answer"},
        headers=csrf_headers(client),
    )
    assert third_card_response.status_code == 201
    third_card_id = third_card_response.json()["card"]["id"]

    assert "second-deck card" in client.get(f"/?deck_id={second_deck_id}").text
    assert "first-deck card" not in client.get(f"/?deck_id={second_deck_id}").text
    assert "first-deck card" in client.get("/").text
    assert "second-deck card" not in client.get("/").text
    assert "second-deck card" in client.get(f"/review?deck_id={second_deck_id}").text
    assert f"deck_id={second_deck_id}" in client.get(
        f"/review?deck_id={second_deck_id}"
    ).text
    shuffled = client.post(
        f"/api/deck/shuffle?deck_id={second_deck_id}",
        headers=csrf_headers(client),
    )
    assert shuffled.status_code == 200
    assert {card["id"] for card in shuffled.json()["cards"]} == {
        second_card_id, third_card_id
    }
    assert [card["position"] for card in shuffled.json()["cards"]] == [0, 1]
    assert "first-deck card" in client.get("/review").text

    assert client.patch(
        f"/api/cards/{first_card}?deck_id={second_deck_id}",
        json={"front": "wrong deck", "back": "wrong deck"},
        headers=csrf_headers(client),
    ).status_code == 404
    assert client.post(
        f"/api/cards?deck_id=999999",
        json={"front": "foreign", "back": "foreign"},
        headers=csrf_headers(client),
    ).status_code == 404

    other = TestClient(create_app(client.app.state.settings))
    register(other, "bob")
    assert other.get(f"/?deck_id={second_deck_id}").status_code == 404
    assert other.patch(
        f"/api/cards/{second_card_id}?deck_id={second_deck_id}",
        json={"front": "stolen", "back": "stolen"},
        headers=csrf_headers(other),
    ).status_code == 404


def test_custom_deck_creation_and_rename_validation(client: TestClient) -> None:
    register(client, "alice")
    csrf = client.cookies.get("vic_csrf")
    first_page = client.get("/")
    first_deck_id = int(re.search(r'data-deck-id="(\d+)"', first_page.text).group(1))

    created = client.post(
        "/decks",
        data={
            "csrf_token": csrf,
            "current_deck_id": first_deck_id,
            "name": "  Biology  ",
        },
        follow_redirects=False,
    )
    assert created.status_code == 303
    biology_id = int(created.headers["location"].split("deck_id=")[1])
    assert "Biology" in client.get(created.headers["location"]).text
    card_id = client.post(
        f"/api/cards?deck_id={biology_id}",
        json={"front": "cell", "back": "membrane"},
        headers=csrf_headers(client),
    ).json()["card"]["id"]

    duplicate = client.post(
        "/decks",
        data={
            "csrf_token": csrf,
            "current_deck_id": biology_id,
            "name": "BIOLOGY",
        },
    )
    assert duplicate.status_code == 400
    assert "already exists" in duplicate.text
    whitespace = client.post(
        "/decks",
        data={
            "csrf_token": csrf,
            "current_deck_id": biology_id,
            "name": "   ",
        },
    )
    assert whitespace.status_code == 400
    assert "must not be empty" in whitespace.text
    too_long = client.post(
        f"/decks/{biology_id}/rename",
        data={"csrf_token": csrf, "name": "x" * 101},
    )
    assert too_long.status_code == 400
    assert "at most 100" in too_long.text

    renamed = client.post(
        f"/decks/{biology_id}/rename",
        data={"csrf_token": csrf, "name": "  Life Sciences  "},
        follow_redirects=False,
    )
    assert renamed.status_code == 303
    page = client.get(renamed.headers["location"])
    assert "Life Sciences" in page.text
    assert "cell" in page.text
    assert client.get(f"/review?deck_id={biology_id}").status_code == 200

    other = TestClient(create_app(client.app.state.settings))
    register(other, "bob")
    assert other.post(
        f"/decks/{biology_id}/rename",
        data={"csrf_token": other.cookies.get("vic_csrf"), "name": "Stolen"},
    ).status_code == 404
    assert client.patch(
        f"/api/cards/{card_id}?deck_id={biology_id}",
        json={"front": "cell", "back": "preserved"},
        headers=csrf_headers(client),
    ).status_code == 200


def test_empty_deck_deletion_requires_csrf_and_preserves_protected_decks(
    client: TestClient,
) -> None:
    register(client, "alice")
    csrf = client.cookies.get("vic_csrf")
    first_page = client.get("/")
    first_deck_id = int(re.search(r'data-deck-id="(\d+)"', first_page.text).group(1))

    last_deck = client.post(
        f"/decks/{first_deck_id}/delete",
        data={"csrf_token": csrf},
    )
    assert last_deck.status_code == 409
    assert "keep at least one deck" in last_deck.text

    second = client.post(
        "/decks",
        data={"csrf_token": csrf, "current_deck_id": first_deck_id},
        follow_redirects=False,
    )
    second_id = int(second.headers["location"].split("deck_id=")[1])
    second_page = client.get(second.headers["location"])
    assert f'action="/decks/{second_id}/delete"' in second_page.text
    assert "return confirm('Delete this empty deck? This cannot be undone.')" in second_page.text
    assert client.post(
        f"/decks/{second_id}/delete", data={}, follow_redirects=False
    ).status_code == 403

    add = client.post(
        f"/api/cards?deck_id={second_id}",
        json={"front": "keep", "back": "me"},
        headers=csrf_headers(client),
    )
    assert add.status_code == 201
    non_empty = client.post(
        f"/decks/{second_id}/delete",
        data={"csrf_token": csrf},
    )
    assert non_empty.status_code == 409
    assert "Only empty decks can be deleted" in non_empty.text
    assert "keep" in client.get(f"/?deck_id={second_id}").text

    third = client.post(
        "/decks",
        data={"csrf_token": csrf, "current_deck_id": second_id},
        follow_redirects=False,
    )
    third_id = int(third.headers["location"].split("deck_id=")[1])
    other = TestClient(create_app(client.app.state.settings))
    register(other, "bob")
    assert other.post(
        f"/decks/{third_id}/delete",
        data={"csrf_token": other.cookies.get("vic_csrf")},
    ).status_code == 404

    deleted = client.post(
        f"/decks/{third_id}/delete",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert deleted.status_code == 303
    assert deleted.headers["location"] == "/"
    assert client.get(f"/?deck_id={third_id}").status_code == 404
    assert "keep" in client.get(f"/?deck_id={second_id}").text


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
    assert "Add some cards to My Deck 1 before reviewing." in page.text
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


def test_formatted_cards_round_trip_in_management_edit_and_review(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice")
    headers = csrf_headers(client)

    front_rich = {
        "version": 1,
        "blocks": [
            {
                "type": "paragraph",
                "runs": [
                    {"text": "Bold ", "bold": True},
                    {"text": "overlap", "bold": True, "italic": True, "underline": True, "color": "blue"},
                ],
            },
            {
                "type": "blockquote",
                "runs": [{"text": "Quoted line 1\nQuoted line 2", "color": "green"}],
            },
        ],
    }
    back_rich = {
        "version": 1,
        "blocks": [
            {
                "type": "paragraph",
                "runs": [
                    {"text": "Green ", "color": "green"},
                    {"text": "Blue ", "color": "blue", "italic": True},
                    {"text": "Red ", "color": "red", "underline": True},
                    {"text": "Black", "color": "black", "bold": True},
                ],
            }
        ],
    }

    created = client.post(
        "/api/cards",
        json={
            "front": "ignored plain",
            "back": "ignored plain",
            "front_rich": front_rich,
            "back_rich": back_rich,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    card = created.json()["card"]
    card_id = card["id"]
    assert card["front"] == "Bold overlap\nQuoted line 1\nQuoted line 2"
    assert card["back"] == "Green Blue Red Black"
    assert card["front_rich"] is not None
    assert card["back_rich"] is not None

    management = client.get("/")
    assert management.status_code == 200
    assert "<strong>Bold </strong>" in management.text
    assert '<span class="fmt-color-blue"><strong><em><u>overlap</u></em></strong></span>' in management.text
    assert 'role="blockquote"' in management.text
    assert '<span class="fmt-color-green">Quoted line 1</span>' in management.text
    assert '<span class="fmt-color-green">Quoted line 2</span>' in management.text
    assert '<span class="fmt-color-green">Green </span>' in management.text
    assert '<span class="fmt-color-blue"><em>Blue </em></span>' in management.text
    assert '<span class="fmt-color-red"><u>Red </u></span>' in management.text
    assert '<span class="fmt-color-black"><strong>Black</strong></span>' in management.text
    assert '<script type="application/json" class="initial-rich-doc">' in management.text

    review = client.get("/review")
    assert review.status_code == 200
    assert '<span class="fmt-color-blue"><strong><em><u>overlap</u></em></strong></span>' in review.text
    assert 'role="blockquote"' in review.text
    assert '<span class="fmt-color-blue"><em>Blue </em></span>' in review.text

    updated = client.patch(
        f"/api/cards/{card_id}",
        json={"front": "Reverted plain", "back": "Also plain", "front_rich": None, "back_rich": None},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["card"]["front_rich"] is None
    assert updated.json()["card"]["back_rich"] is None
    reloaded = client.get("/")
    assert "Reverted plain" in reloaded.text
    assert '<span class="fmt-color-blue">' not in reloaded.text


def test_formatting_toolbar_accessibility_attributes_present(client: TestClient) -> None:
    register(client, "alice")
    add_card(client, "sample front", "sample back")
    page = client.get("/")
    assert page.status_code == 200
    assert page.text.count('role="toolbar"') == 4
    assert 'aria-label="Front formatting"' in page.text
    assert 'aria-label="Back formatting"' in page.text
    for label in ("Bold", "Italic", "Underline"):
        assert f'aria-label="{label}"' in page.text
    assert 'data-command="blockquote"' not in page.text
    assert 'aria-label="Block quote"' not in page.text
    for color in ("Black", "Green", "Red", "Blue"):
        assert f'aria-label="Text color: {color}"' in page.text
    for removed in ("Orange", "Pink"):
        assert f'aria-label="Text color: {removed}"' not in page.text


def test_formatting_validation_boundaries_and_xss_defense(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice")
    headers = csrf_headers(client)

    ok_5000 = client.post(
        "/api/cards",
        json={
            "front": "",
            "back": "ok",
            "front_rich": {
                "version": 1,
                "blocks": [{"type": "paragraph", "runs": [{"text": "😀" * 5000, "bold": True}]}],
            },
        },
        headers=headers,
    )
    assert ok_5000.status_code == 201

    too_long = client.post(
        "/api/cards",
        json={
            "front": "",
            "back": "ok",
            "front_rich": {
                "version": 1,
                "blocks": [{"type": "paragraph", "runs": [{"text": "😀" * 5001, "bold": True}]}],
            },
        },
        headers=headers,
    )
    assert too_long.status_code == 422

    empty_rich = client.post(
        "/api/cards",
        json={
            "front": "",
            "back": "ok",
            "front_rich": {
                "version": 1,
                "blocks": [{"type": "blockquote", "runs": [{"text": "   ", "bold": True}]}],
            },
        },
        headers=headers,
    )
    assert empty_rich.status_code == 422

    bad_color = client.post(
        "/api/cards",
        json={
            "front": "",
            "back": "ok",
            "front_rich": {
                "version": 1,
                "blocks": [{"type": "paragraph", "runs": [{"text": "hi", "color": "purple"}]}],
            },
        },
        headers=headers,
    )
    assert bad_color.status_code == 422

    hostile = client.post(
        "/api/cards",
        json={
            "front": "<script>alert(1)</script>",
            "back": "",
            "back_rich": {
                "version": 1,
                "blocks": [
                    {
                        "type": "paragraph",
                        "runs": [{"text": "</script><script>alert(2)</script>", "bold": True}],
                    }
                ],
            },
        },
        headers=headers,
    )
    assert hostile.status_code == 201
    hostile_id = hostile.json()["card"]["id"]

    page = client.get("/")
    assert "<script>alert(1)</script>" not in page.text
    assert "<script>alert(2)</script>" not in page.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page.text
    assert "<strong>&lt;/script&gt;&lt;script&gt;alert(2)&lt;/script&gt;</strong>" in page.text

    # Account isolation and CSRF checks remain intact for formatted updates.
    no_csrf = client.patch(
        f"/api/cards/{hostile_id}",
        json={"front": "x", "back": "y"},
    )
    assert no_csrf.status_code == 403

    other = TestClient(create_app(settings))
    register(other, "bob")
    assert other.patch(
        f"/api/cards/{hostile_id}",
        json={
            "front": "stolen",
            "back": "stolen",
            "front_rich": {
                "version": 1,
                "blocks": [{"type": "paragraph", "runs": [{"text": "stolen", "bold": True}]}],
            },
        },
        headers=csrf_headers(other),
    ).status_code == 404


def test_api_docs_routes_are_hidden_by_default(
    client: TestClient, settings: Settings
) -> None:
    assert settings.enable_docs is False
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_api_docs_routes_can_be_enabled(settings: Settings) -> None:
    enabled = Settings(
        database_path=settings.database_path,
        cookie_secure=False,
        enable_docs=True,
    )
    with TestClient(create_app(enabled)) as docs_client:
        assert docs_client.get("/docs").status_code == 200
        assert docs_client.get("/redoc").status_code == 200
        schema = docs_client.get("/openapi.json")
        assert schema.status_code == 200
        assert schema.json()["info"]["title"] == "Virtual Index Cards"


def test_openapi_version_matches_package_version(settings: Settings) -> None:
    from virtual_index_card import __version__

    enabled = Settings(
        database_path=settings.database_path,
        cookie_secure=False,
        enable_docs=True,
    )
    with TestClient(create_app(enabled)) as docs_client:
        assert docs_client.get("/openapi.json").json()["info"]["version"] == __version__


# --- Public read-only deck sharing (#4) -------------------------------------


def _create_share(client: TestClient, deck_id: str) -> str:
    """Create or rotate a share link and return its public path."""
    response = client.post(
        f"/decks/{deck_id}/share",
        data={"csrf_token": client.cookies.get("vic_csrf")},
        follow_redirects=False,
    )
    assert response.status_code == 200, response.text
    match = re.search(r'id="share-url" class="share-url" value="([^"]+)"', response.text)
    assert match is not None, response.text
    return "/" + match.group(1).split("/", 3)[3]


def _deck_id(client: TestClient) -> str:
    page = client.get("/")
    match = re.search(r'data-deck-id="(\d+)"', page.text)
    assert match is not None
    return match.group(1)


def test_share_link_is_read_only_and_anonymous(client: TestClient, settings: Settings) -> None:
    register(client, "alice")
    headers = csrf_headers(client)
    client.post("/api/cards", json={"front": "Q1", "back": "A1"}, headers=headers)
    client.post("/api/cards", json={"front": "Q2", "back": "A2"}, headers=headers)
    deck_id = _deck_id(client)
    share_path = _create_share(client, deck_id)

    anonymous = TestClient(create_app(settings))
    view = anonymous.get(share_path)
    assert view.status_code == 200
    assert view.headers["cache-control"] == "no-store"
    assert view.headers["x-robots-tag"] == "noindex, nofollow"
    assert "Q1" in view.text and "A1" in view.text
    assert 'name="robots"' in view.text
    # Only the shared deck's cards, and none of the owner's private surface.
    assert "Q2" not in view.text
    assert "alice" not in view.text
    assert "admin/requests" not in view.text
    assert "csrf-token" not in view.text

    # Review-order navigation works without authentication.
    next_link = re.search(r'href="(/s/[^"]+index=\d+)"[^>]*rel="next"', view.text)
    assert next_link is not None
    assert anonymous.get(next_link.group(1)).status_code == 200

    # Every mutation path is rejected for an anonymous viewer.
    assert anonymous.post("/api/cards", json={"front": "x", "back": "y"}).status_code == 401
    assert anonymous.post("/api/deck/shuffle").status_code == 401
    assert anonymous.patch("/api/cards/1", json={"front": "x", "back": "y"}).status_code == 401
    assert anonymous.delete("/api/cards/1").status_code == 401
    assert anonymous.post(f"/decks/{deck_id}/share").status_code == 401
    assert anonymous.post(f"/decks/{deck_id}/share/revoke").status_code == 401
    landing = anonymous.get("/", follow_redirects=False)
    assert landing.status_code == 303
    assert landing.headers["location"] == "/login"


def test_share_requires_owner_and_csrf(client: TestClient, settings: Settings) -> None:
    register(client, "alice")
    client.post("/api/cards", json={"front": "Q", "back": "A"}, headers=csrf_headers(client))
    deck_id = _deck_id(client)

    no_csrf = client.post(f"/decks/{deck_id}/share", data={}, follow_redirects=False)
    assert no_csrf.status_code == 403

    other = TestClient(create_app(settings))
    register(other, "bob")
    foreign = other.post(
        f"/decks/{deck_id}/share",
        data={"csrf_token": other.cookies.get("vic_csrf")},
        follow_redirects=False,
    )
    assert foreign.status_code == 404
    # Bob's own deck is unaffected by Alice's link.
    assert "alice" not in other.get("/").text


def test_share_rotation_and_revocation(client: TestClient, settings: Settings) -> None:
    register(client, "alice")
    deck_id = _deck_id(client)
    first = _create_share(client, deck_id)
    anonymous = TestClient(create_app(settings))
    assert anonymous.get(first).status_code == 200

    rotated = client.post(
        f"/decks/{deck_id}/share/rotate",
        data={"csrf_token": client.cookies.get("vic_csrf")},
        follow_redirects=False,
    )
    assert rotated.status_code == 200
    assert "rotated" in rotated.text.lower()
    new_path = "/" + re.search(
        r'id="share-url" class="share-url" value="([^"]+)"', rotated.text
    ).group(1).split("/", 3)[3]
    assert new_path != first
    assert anonymous.get(first).status_code == 404
    assert anonymous.get(new_path).status_code == 200

    revoked = client.post(
        f"/decks/{deck_id}/share/revoke",
        data={"csrf_token": client.cookies.get("vic_csrf")},
        follow_redirects=True,
    )
    assert revoked.status_code == 200
    assert "revoked" in revoked.text
    assert "Create public link" in revoked.text
    assert anonymous.get(new_path).status_code == 404


def test_unknown_and_malformed_tokens_are_indistinguishable(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice")
    anonymous = TestClient(create_app(settings))
    unknown = anonymous.get("/s/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    malformed = anonymous.get("/s/not-a-token")
    assert unknown.status_code == malformed.status_code == 404
    assert unknown.text == malformed.text
    assert "alice" not in unknown.text


def test_share_tokens_are_stored_hashed_only(client: TestClient, settings: Settings) -> None:
    register(client, "alice")
    deck_id = _deck_id(client)
    share_path = _create_share(client, deck_id)
    token = share_path.rsplit("/", 1)[1]
    from contextlib import closing

    from virtual_index_card.db import connect

    with closing(connect(settings.database_path)) as connection:
        row = connection.execute("SELECT token_hash FROM deck_shares").fetchone()
    assert row is not None
    assert row["token_hash"] != token
    assert len(row["token_hash"]) == 64
    with closing(connect(settings.database_path)) as connection:
        assert connection.execute(
            "SELECT COUNT(*) AS n FROM deck_shares WHERE token_hash = ?", (token,)
        ).fetchone()["n"] == 0


def test_deleting_a_deck_revokes_its_share(client: TestClient, settings: Settings) -> None:
    register(client, "alice")
    deck_id = _deck_id(client)
    # A second deck so the first is deletable while empty.
    client.post(
        "/decks",
        data={"csrf_token": client.cookies.get("vic_csrf"), "current_deck_id": deck_id},
        follow_redirects=False,
    )
    share_path = _create_share(client, deck_id)
    anonymous = TestClient(create_app(settings))
    assert anonymous.get(share_path).status_code == 200

    deleted = client.post(
        f"/decks/{deck_id}/delete",
        data={"csrf_token": client.cookies.get("vic_csrf")},
        follow_redirects=False,
    )
    assert deleted.status_code == 303
    assert anonymous.get(share_path).status_code == 404
    from contextlib import closing

    from virtual_index_card.db import connect

    with closing(connect(settings.database_path)) as connection:
        assert connection.execute("SELECT COUNT(*) AS n FROM deck_shares").fetchone()["n"] == 0


def test_formatted_cards_render_in_the_shared_view(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice")
    response = client.post(
        "/api/cards",
        json={
            "front": "bold front",
            "back": "plain back",
            "front_rich": {
                "version": 1,
                "blocks": [
                    {"type": "paragraph", "runs": [{"text": "bold front", "bold": True}]}
                ],
            },
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 201
    share_path = _create_share(client, _deck_id(client))
    view = TestClient(create_app(settings)).get(share_path)
    assert view.status_code == 200
    assert "<strong>bold front</strong>" in view.text


def test_unformatted_shared_pages_escape_markup_like_text(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice")
    client.post(
        "/api/cards",
        json={"front": "<script>alert(1)</script>", "back": "2 < 3"},
        headers=csrf_headers(client),
    )
    share_path = _create_share(client, _deck_id(client))
    view = TestClient(create_app(settings)).get(share_path)
    assert "<script>alert(1)</script>" not in view.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in view.text


# --- Deck export (#5 groundwork) --------------------------------------------


def test_export_is_versioned_and_owned_only(client: TestClient, settings: Settings) -> None:
    import json as jsonlib

    register(client, "alice")
    headers = csrf_headers(client)
    client.post("/api/cards", json={"front": "Q1", "back": "A1"}, headers=headers)
    client.post("/api/cards", json={"front": "Q2", "back": "A2"}, headers=headers)
    deck_id = _deck_id(client)

    response = client.get(f"/decks/{deck_id}/export.json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]
    payload = jsonlib.loads(response.text)
    assert payload["format"] == "virtual-index-card/deck"
    assert payload["version"] == 1
    assert payload["deck"]["name"] == "My Deck 1"
    assert [card["front"] for card in payload["cards"]] == ["Q1", "Q2"]
    # Never credentials, internal ids, or sharing tokens.
    assert "alice" not in response.text
    assert "token" not in response.text.lower()
    assert "user_id" not in response.text

    anonymous = TestClient(create_app(settings))
    assert anonymous.get(f"/decks/{deck_id}/export.json").status_code == 401
    assert anonymous.get(f"/decks/{deck_id}/export.json", follow_redirects=False).status_code == 401

    other = TestClient(create_app(settings))
    register(other, "bob")
    assert other.get(f"/decks/{deck_id}/export.json").status_code == 404


def test_export_enforces_configured_limits(tmp_path) -> None:
    from virtual_index_card.config import Settings

    settings = Settings(
        database_path=tmp_path / "limits.sqlite3",
        cookie_secure=False,
        max_export_rows=1,
    )
    with TestClient(create_app(settings)) as client:
        register(client, "alice")
        headers = csrf_headers(client)
        client.post("/api/cards", json={"front": "Q1", "back": "A1"}, headers=headers)
        client.post("/api/cards", json={"front": "Q2", "back": "A2"}, headers=headers)
        response = client.get(f"/decks/{_deck_id(client)}/export.json")
        assert response.status_code == 413
        assert "VIC_MAX_EXPORT_ROWS" in response.text
