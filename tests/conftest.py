from collections.abc import Iterator
from contextlib import closing

import pytest
from fastapi.testclient import TestClient
from sqlite3 import Connection

from virtual_index_card import repository as repo
from virtual_index_card.app import create_app
from virtual_index_card.config import Settings
from virtual_index_card.db import connect, initialize
from virtual_index_card.domain import utc_now
from virtual_index_card.security import hash_password

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin-password-123"


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


def make_admin(settings: Settings) -> None:
    """Idempotently create the default administrator for a test database."""
    initialize(settings.database_path)
    with closing(connect(settings.database_path)) as connection:
        with connection:
            existing = repo.get_user_by_username(connection, ADMIN_USERNAME)
            if existing is None:
                salt, digest = hash_password(ADMIN_PASSWORD)
                repo.create_user(
                    connection, ADMIN_USERNAME, salt, digest, utc_now(), role="admin"
                )
            else:
                repo.set_user_role(connection, int(existing["id"]), "admin")


def admin_client(settings: Settings) -> TestClient:
    make_admin(settings)
    admin = TestClient(create_app(settings))
    response = admin.post(
        "/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    return admin


def pending_request_id(settings: Settings, username: str) -> int:
    with closing(connect(settings.database_path)) as connection:
        row = connection.execute(
            "SELECT id FROM account_requests "
            "WHERE username = ? COLLATE NOCASE AND status = 'pending'",
            (username,),
        ).fetchone()
    assert row is not None, f"No pending request for {username!r}."
    return int(row["id"])


def register(client: TestClient, username: str, password: str = "correct horse battery") -> None:
    """Drive the full request → administrator approval → login flow.

    Leaves `client` logged in as the new account, mirroring the old helper's contract.
    """
    settings: Settings = client.app.state.settings
    make_admin(settings)
    response = client.post(
        "/register",
        data={"username": username},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    admin = admin_client(settings)
    approval = admin.post(
        f"/admin/requests/{pending_request_id(settings, username)}/approve",
        data={
            "account_username": username,
            "account_password": password,
            "csrf_token": admin.cookies.get("vic_csrf"),
        },
        follow_redirects=False,
    )
    assert approval.status_code == 200, approval.text
    login = client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    assert login.status_code == 303, login.text


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("vic_csrf")
    assert token is not None
    return {"X-CSRF-Token": token}
