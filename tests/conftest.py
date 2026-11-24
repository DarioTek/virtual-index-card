from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlite3 import Connection

from virtual_index_card.app import create_app
from virtual_index_card.config import Settings
from virtual_index_card.db import connect, initialize


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(database_path=tmp_path / "index-cards.sqlite3", cookie_secure=False)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def connection(settings: Settings) -> Iterator[Connection]:
    initialize(settings.database_path)
    conn = connect(settings.database_path)
    try:
        yield conn
    finally:
        conn.close()


def register(client: TestClient, username: str, password: str = "correct horse battery") -> None:
    response = client.post(
        "/register",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("vic_csrf")
    assert token is not None
    return {"X-CSRF-Token": token}
