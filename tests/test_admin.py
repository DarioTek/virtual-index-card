import re
import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from virtual_index_card import repository as repo
from virtual_index_card.app import create_app
from virtual_index_card.config import Settings
from virtual_index_card.db import connect
from virtual_index_card.domain import utc_now
from virtual_index_card.security import hash_password
from tests.conftest import admin_client, csrf_headers, pending_request_id, register

V1_SCHEMA = """
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    salt          TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_sessions_expiry ON sessions(expires_at);
CREATE TABLE cards (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    front      TEXT NOT NULL,
    back       TEXT NOT NULL,
    position   INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_cards_user_position ON cards(user_id, position);
"""


def test_request_form_is_shown(client: TestClient) -> None:
    page = client.get("/register")
    assert page.status_code == 200
    assert "Request an account" in page.text
    assert "Desired account name" in page.text


def test_request_does_not_create_account_or_session(client: TestClient, settings: Settings) -> None:
    response = client.post("/register", data={"username": "alice"}, follow_redirects=False)
    assert response.status_code == 303
    assert client.get("/register/received").status_code == 200
    assert client.cookies.get("vic_session") is None

    login = client.post(
        "/login",
        data={"username": "alice", "password": "correct horse battery"},
        follow_redirects=False,
    )
    assert login.status_code == 401

    connection = sqlite3.connect(settings.database_path)
    try:
        users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        pending = connection.execute(
            "SELECT COUNT(*) FROM account_requests WHERE status = 'pending'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert users == 0
    assert pending == 1


def test_admin_routes_require_administrator(client: TestClient, settings: Settings) -> None:
    anonymous = client.get("/admin/requests", follow_redirects=False)
    assert anonymous.status_code == 303
    assert anonymous.headers["location"] == "/login"

    register(client, "alice")
    forbidden = client.get("/admin/requests")
    assert forbidden.status_code == 403
    assert "Administrator access required" in forbidden.text
    assert 'href="/admin/requests"' not in forbidden.text

    approval = client.post(
        "/admin/requests/1/approve",
        data={"csrf_token": client.cookies.get("vic_csrf")},
        follow_redirects=False,
    )
    assert approval.status_code == 403


def test_admin_sees_requests_and_approves(client: TestClient, settings: Settings) -> None:
    client.post(
        "/register",
        data={"username": "alice", "contact": "alice@example.com", "note": "hi"},
        follow_redirects=False,
    )
    admin = admin_client(settings)
    page = admin.get("/admin/requests")
    assert page.status_code == 200
    assert "alice" in page.text
    assert "alice@example.com" in page.text
    assert "hi" in page.text
    assert 'href="/admin/requests"' in admin.get("/").text

    approval = admin.post(
        f"/admin/requests/{pending_request_id(settings, 'alice')}/approve",
        data={
            "account_username": "alice",
            "account_password": "chosen-password-123",
            "csrf_token": admin.cookies.get("vic_csrf"),
        },
        follow_redirects=False,
    )
    assert approval.status_code == 200, approval.text
    assert "Account created" in approval.text
    assert "chosen-password-123" in approval.text
    assert 'id="credential-password"' in approval.text

    login = client.post(
        "/login",
        data={"username": "alice", "password": "chosen-password-123"},
        follow_redirects=False,
    )
    assert login.status_code == 303


def test_approve_generates_password_when_left_blank(
    client: TestClient, settings: Settings
) -> None:
    client.post("/register", data={"username": "alice"}, follow_redirects=False)
    admin = admin_client(settings)
    approval = admin.post(
        f"/admin/requests/{pending_request_id(settings, 'alice')}/approve",
        data={"account_username": "alice", "csrf_token": admin.cookies.get("vic_csrf")},
    )
    assert approval.status_code == 200
    match = re.search(r'id="credential-password">([^<]+)<', approval.text)
    assert match is not None
    generated = match.group(1)
    assert len(generated) >= 8

    login = client.post(
        "/login", data={"username": "alice", "password": generated}, follow_redirects=False
    )
    assert login.status_code == 303


def test_approve_can_change_account_name(client: TestClient, settings: Settings) -> None:
    client.post("/register", data={"username": "alice"}, follow_redirects=False)
    admin = admin_client(settings)
    approval = admin.post(
        f"/admin/requests/{pending_request_id(settings, 'alice')}/approve",
        data={
            "account_username": "alice-smith",
            "account_password": "chosen-password-123",
            "csrf_token": admin.cookies.get("vic_csrf"),
        },
    )
    assert approval.status_code == 200
    assert "alice-smith" in approval.text
    login = client.post(
        "/login",
        data={"username": "alice-smith", "password": "chosen-password-123"},
        follow_redirects=False,
    )
    assert login.status_code == 303


def test_approval_rejected_when_account_name_taken(
    client: TestClient, settings: Settings
) -> None:
    register(client, "bob", password="bob-password-123")
    client.post("/register", data={"username": "alice"}, follow_redirects=False)
    admin = admin_client(settings)
    approval = admin.post(
        f"/admin/requests/{pending_request_id(settings, 'alice')}/approve",
        data={
            "account_username": "BOB",
            "account_password": "chosen-password-123",
            "csrf_token": admin.cookies.get("vic_csrf"),
        },
    )
    assert approval.status_code == 400
    assert "already taken" in approval.text

    pending = admin.get("/admin/requests")
    assert "alice" in pending.text


def test_approval_requires_csrf(client: TestClient, settings: Settings) -> None:
    client.post("/register", data={"username": "alice"}, follow_redirects=False)
    admin = admin_client(settings)
    request_id = pending_request_id(settings, "alice")
    approval = admin.post(
        f"/admin/requests/{request_id}/approve", data={"account_username": "alice"}
    )
    assert approval.status_code == 403


def test_reject_request(client: TestClient, settings: Settings) -> None:
    client.post("/register", data={"username": "alice"}, follow_redirects=False)
    admin = admin_client(settings)
    request_id = pending_request_id(settings, "alice")
    rejection = admin.post(
        f"/admin/requests/{request_id}/reject",
        data={"csrf_token": admin.cookies.get("vic_csrf")},
        follow_redirects=False,
    )
    assert rejection.status_code == 303

    login = client.post(
        "/login",
        data={"username": "alice", "password": "correct horse battery"},
        follow_redirects=False,
    )
    assert login.status_code == 401

    again = admin.post(
        f"/admin/requests/{request_id}/reject",
        data={"csrf_token": admin.cookies.get("vic_csrf")},
    )
    assert again.status_code == 409


def test_decided_requests_cannot_be_approved(
    client: TestClient, settings: Settings
) -> None:
    client.post("/register", data={"username": "alice"}, follow_redirects=False)
    admin = admin_client(settings)
    request_id = pending_request_id(settings, "alice")
    admin.post(
        f"/admin/requests/{request_id}/reject",
        data={"csrf_token": admin.cookies.get("vic_csrf")},
    )
    approval = admin.post(
        f"/admin/requests/{request_id}/approve",
        data={
            "account_username": "alice",
            "account_password": "chosen-password-123",
            "csrf_token": admin.cookies.get("vic_csrf"),
        },
    )
    assert approval.status_code == 409


def test_duplicate_pending_request_is_rejected(client: TestClient) -> None:
    client.post("/register", data={"username": "alice"}, follow_redirects=False)
    duplicate = client.post("/register", data={"username": "ALICE"})
    assert duplicate.status_code == 400
    assert "awaiting review" in duplicate.text


def test_request_validation(client: TestClient) -> None:
    bad_username = client.post("/register", data={"username": "ab"})
    assert bad_username.status_code == 400

    bad_chars = client.post("/register", data={"username": "not ok!"})
    assert bad_chars.status_code == 400

    bad_contact = client.post(
        "/register", data={"username": "valid-name", "contact": "x" * 201}
    )
    assert bad_contact.status_code == 400
    assert "Contact" in bad_contact.text

    bad_note = client.post(
        "/register", data={"username": "valid-name", "note": "x" * 1001}
    )
    assert bad_note.status_code == 400
    assert "Note" in bad_note.text


def test_approval_page_does_not_leak_password_afterwards(
    client: TestClient, settings: Settings
) -> None:
    client.post("/register", data={"username": "alice"}, follow_redirects=False)
    admin = admin_client(settings)
    admin.post(
        f"/admin/requests/{pending_request_id(settings, 'alice')}/approve",
        data={
            "account_username": "alice",
            "account_password": "chosen-password-123",
            "csrf_token": admin.cookies.get("vic_csrf"),
        },
    )
    page = admin.get("/admin/requests")
    assert "chosen-password-123" not in page.text

    connection = sqlite3.connect(settings.database_path)
    try:
        row = connection.execute(
            "SELECT salt, password_hash FROM users WHERE username = 'alice'"
        ).fetchone()
    finally:
        connection.close()
    assert "chosen-password-123" not in (row[0] + row[1])


def test_reset_password_generates_new_credentials_and_signs_out(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice", password="old-password-123")
    connection = sqlite3.connect(settings.database_path)
    try:
        user_id = connection.execute(
            "SELECT id FROM users WHERE username = 'alice'"
        ).fetchone()[0]
    finally:
        connection.close()

    admin = admin_client(settings)
    reset = admin.post(
        f"/admin/users/{user_id}/reset-password",
        data={"csrf_token": admin.cookies.get("vic_csrf")},
    )
    assert reset.status_code == 200
    match = re.search(r'id="credential-password">([^<]+)<', reset.text)
    assert match is not None
    new_password = match.group(1)

    assert client.get("/", follow_redirects=False).headers["location"] == "/login"

    old_login = client.post(
        "/login",
        data={"username": "alice", "password": "old-password-123"},
        follow_redirects=False,
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/login",
        data={"username": "alice", "password": new_password},
        follow_redirects=False,
    )
    assert new_login.status_code == 303


def test_reset_password_is_admin_only_and_skips_admins(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice")
    connection = sqlite3.connect(settings.database_path)
    try:
        admin_id = connection.execute(
            "SELECT id FROM users WHERE role = 'admin'"
        ).fetchone()[0]
    finally:
        connection.close()

    forbidden = client.post(
        f"/admin/users/{admin_id}/reset-password",
        data={"csrf_token": client.cookies.get("vic_csrf")},
    )
    assert forbidden.status_code == 403

    admin = admin_client(settings)
    refused = admin.post(
        f"/admin/users/{admin_id}/reset-password",
        data={"csrf_token": admin.cookies.get("vic_csrf")},
    )
    assert refused.status_code == 400
    assert "Administrator passwords" in refused.text


def test_env_admin_bootstrap_creates_administrator(tmp_path) -> None:
    database = tmp_path / "bootstrap.sqlite3"
    settings = Settings(
        database_path=database,
        admin_username="root",
        admin_password="bootstrap-password-1",
    )
    with TestClient(create_app(settings)) as client:
        login = client.post(
            "/login",
            data={"username": "root", "password": "bootstrap-password-1"},
            follow_redirects=False,
        )
        assert login.status_code == 303
        page = client.get("/admin/requests")
        assert page.status_code == 200


def test_env_admin_bootstrap_requires_password_for_new_user(tmp_path) -> None:
    database = tmp_path / "broken.sqlite3"
    settings = Settings(database_path=database, admin_username="root")
    with pytest.raises(RuntimeError, match="Administrator bootstrap"):
        create_app(settings)


def test_env_admin_bootstrap_promotes_existing_user(tmp_path) -> None:
    database = tmp_path / "promote.sqlite3"
    settings = Settings(database_path=database)
    with TestClient(create_app(settings)) as client:
        register(client, "alice")
        assert client.get("/admin/requests").status_code == 403
    promoted = Settings(
        database_path=database,
        admin_username="alice",
        admin_password="new-admin-password-1",
    )
    with TestClient(create_app(promoted)) as client:
        login = client.post(
            "/login",
            data={"username": "alice", "password": "new-admin-password-1"},
            follow_redirects=False,
        )
        assert login.status_code == 303
        assert client.get("/admin/requests").status_code == 200


def test_create_admin_cli_creates_and_promotes(tmp_path, monkeypatch, capsys) -> None:
    from virtual_index_card import create_admin

    database = tmp_path / "cli.sqlite3"
    monkeypatch.setenv("VIC_DATABASE_PATH", str(database))

    monkeypatch.setattr("sys.argv", ["create_admin", "boss"])
    assert create_admin.main() == 0
    created = capsys.readouterr().out
    match = re.search(r"Temporary password \(shown once\): (\S+)", created)
    assert match is not None
    password = match.group(1)

    with TestClient(create_app()) as client:
        login = client.post(
            "/login",
            data={"username": "boss", "password": password},
            follow_redirects=False,
        )
        assert login.status_code == 303

    monkeypatch.setattr("sys.argv", ["create_admin", "boss"])
    assert create_admin.main() == 0
    assert "promoted" in capsys.readouterr().out


def test_migration_from_schema_v1(tmp_path) -> None:
    database = tmp_path / "v1.sqlite3"
    connection = sqlite3.connect(database)
    try:
        connection.executescript(V1_SCHEMA)
        from virtual_index_card.security import hash_password

        salt, digest = hash_password("legacy-password-1")
        connection.execute(
            "INSERT INTO users (username, salt, password_hash, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("legacy", salt, digest, "2026-11-24T00:00:00+00:00"),
        )
        connection.execute("PRAGMA user_version = 1")
        connection.commit()
    finally:
        connection.close()

    settings = Settings(database_path=database)
    with TestClient(create_app(settings)) as client:
        login = client.post(
            "/login",
            data={"username": "legacy", "password": "legacy-password-1"},
            follow_redirects=False,
        )
        assert login.status_code == 303
        assert client.get("/admin/requests").status_code == 403

    migrated = sqlite3.connect(database)
    try:
        version = migrated.execute("PRAGMA user_version").fetchone()[0]
        role = migrated.execute(
            "SELECT role FROM users WHERE username = 'legacy'"
        ).fetchone()[0]
        tables = {
            row[0]
            for row in migrated.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        migrated.close()
    assert version == 2
    assert role == "user"
    assert "account_requests" in tables


def test_fresh_databases_use_schema_v2(tmp_path) -> None:
    database = tmp_path / "fresh.sqlite3"
    settings = Settings(database_path=database)
    create_app(settings)
    connection = sqlite3.connect(database)
    try:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
    finally:
        connection.close()
    assert version == 2


def test_unsupported_schema_version_is_rejected(tmp_path) -> None:
    database = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA user_version = 99")
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(RuntimeError, match="Unsupported database schema version"):
        create_app(Settings(database_path=database))


# --- Administrator: user management (/admin/users) --------------------------


def _create_user_directly(
    settings: Settings, username: str, password: str, role: str = "user"
) -> int:
    with closing(connect(settings.database_path)) as connection:
        with connection:
            salt, digest = hash_password(password)
            return repo.create_user(connection, username, salt, digest, utc_now(), role=role)


def test_admin_users_page_lists_accounts(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice")
    client.post(
        "/api/cards",
        json={"front": "f", "back": "b"},
        headers=csrf_headers(client),
    )

    admin = admin_client(settings)
    page = admin.get("/admin/users")
    assert page.status_code == 200
    assert "alice" in page.text
    assert "admin" in page.text
    assert "<td>1</td>" in page.text
    assert 'href="/admin/users"' in admin.get("/").text


def test_admin_users_page_requires_administrator(client: TestClient) -> None:
    anonymous = client.get("/admin/users", follow_redirects=False)
    assert anonymous.status_code == 303
    assert anonymous.headers["location"] == "/login"

    register(client, "alice")
    forbidden = client.get("/admin/users")
    assert forbidden.status_code == 403
    assert 'href="/admin/users"' not in client.get("/").text


def test_admin_users_page_marks_admins_protected(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice")
    admin = admin_client(settings)
    page = admin.get("/admin/users")
    assert "Protected" in page.text
    connection = sqlite3.connect(settings.database_path)
    try:
        alice_id = connection.execute(
            "SELECT id FROM users WHERE username = 'alice'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert f'action="/admin/users/{alice_id}/delete"' in page.text


def test_delete_user_removes_account_cards_and_sessions(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice")
    client.post(
        "/api/cards",
        json={"front": "secret", "back": "gone"},
        headers=csrf_headers(client),
    )
    connection = sqlite3.connect(settings.database_path)
    try:
        alice_id = connection.execute(
            "SELECT id FROM users WHERE username = 'alice'"
        ).fetchone()[0]
        assert connection.execute(
            "SELECT COUNT(*) FROM cards WHERE user_id = ?", (alice_id,)
        ).fetchone()[0] == 1
    finally:
        connection.close()

    admin = admin_client(settings)
    deletion = admin.post(
        f"/admin/users/{alice_id}/delete",
        data={"csrf_token": admin.cookies.get("vic_csrf")},
        follow_redirects=False,
    )
    assert deletion.status_code == 303

    connection = sqlite3.connect(settings.database_path)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM users WHERE id = ?", (alice_id,)
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM cards WHERE user_id = ?", (alice_id,)
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM sessions WHERE user_id = ?", (alice_id,)
        ).fetchone()[0] == 0
        audit = connection.execute(
            "SELECT status, created_user_id, decided_by FROM account_requests"
        ).fetchone()
    finally:
        connection.close()
    # The approval audit trail survives with user references nulled out.
    assert audit[0] == "approved"
    assert audit[1] is None

    login = client.post(
        "/login",
        data={"username": "alice", "password": "correct horse battery"},
        follow_redirects=False,
    )
    assert login.status_code == 401


def test_delete_user_rejects_administrator_accounts(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice")
    admin = admin_client(settings)
    connection = sqlite3.connect(settings.database_path)
    try:
        admin_id = connection.execute(
            "SELECT id FROM users WHERE role = 'admin'"
        ).fetchone()[0]
    finally:
        connection.close()

    refused = admin.post(
        f"/admin/users/{admin_id}/delete",
        data={"csrf_token": admin.cookies.get("vic_csrf")},
    )
    assert refused.status_code == 400
    assert "Administrator accounts cannot be deleted" in refused.text

    connection = sqlite3.connect(settings.database_path)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM users WHERE id = ?", (admin_id,)
        ).fetchone()[0] == 1
    finally:
        connection.close()


def test_delete_user_requires_csrf_and_existing_user(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice")
    admin = admin_client(settings)
    connection = sqlite3.connect(settings.database_path)
    try:
        alice_id = connection.execute(
            "SELECT id FROM users WHERE username = 'alice'"
        ).fetchone()[0]
    finally:
        connection.close()

    no_csrf = admin.post(f"/admin/users/{alice_id}/delete")
    assert no_csrf.status_code == 403

    missing = admin.post(
        "/admin/users/999999/delete",
        data={"csrf_token": admin.cookies.get("vic_csrf")},
    )
    assert missing.status_code == 404


def test_delete_user_is_admin_only(client: TestClient, settings: Settings) -> None:
    register(client, "alice")
    admin = admin_client(settings)
    connection = sqlite3.connect(settings.database_path)
    try:
        admin_id = connection.execute(
            "SELECT id FROM users WHERE role = 'admin'"
        ).fetchone()[0]
    finally:
        connection.close()

    forbidden = client.post(
        f"/admin/users/{admin_id}/delete",
        data={"csrf_token": client.cookies.get("vic_csrf")},
    )
    assert forbidden.status_code == 403


def test_reset_password_works_for_user_not_created_by_approval(
    client: TestClient, settings: Settings
) -> None:
    uid = _create_user_directly(settings, "legacyuser", "legacy-password-9")
    admin = admin_client(settings)
    reset = admin.post(
        f"/admin/users/{uid}/reset-password",
        data={"csrf_token": admin.cookies.get("vic_csrf")},
    )
    assert reset.status_code == 200
    match = re.search(r'id="credential-password">([^<]+)<', reset.text)
    assert match is not None

    old_login = client.post(
        "/login",
        data={"username": "legacyuser", "password": "legacy-password-9"},
        follow_redirects=False,
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/login",
        data={"username": "legacyuser", "password": match.group(1)},
        follow_redirects=False,
    )
    assert new_login.status_code == 303


# --- Administrator: own profile (/admin/profile) -----------------------------


def test_admin_profile_requires_administrator(client: TestClient) -> None:
    anonymous = client.get("/admin/profile", follow_redirects=False)
    assert anonymous.status_code == 303
    assert anonymous.headers["location"] == "/login"

    register(client, "alice")
    assert client.get("/admin/profile").status_code == 403
    assert 'href="/admin/profile"' not in client.get("/").text


def test_admin_profile_shows_current_username(
    client: TestClient, settings: Settings
) -> None:
    admin = admin_client(settings)
    page = admin.get("/admin/profile")
    assert page.status_code == 200
    assert 'value="admin"' in page.text
    assert 'href="/admin/profile"' in admin.get("/").text


def test_change_username_keeps_session_and_rename(
    client: TestClient, settings: Settings
) -> None:
    admin = admin_client(settings)
    response = admin.post(
        "/admin/profile",
        data={
            "username": "boss2",
            "current_password": "admin-password-123",
            "csrf_token": admin.cookies.get("vic_csrf"),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    assert admin.get("/").status_code == 200
    assert "boss2" in admin.get("/").text

    new_client = TestClient(create_app(settings))
    old_login = new_client.post(
        "/login",
        data={"username": "admin", "password": "admin-password-123"},
        follow_redirects=False,
    )
    assert old_login.status_code == 401
    new_login = new_client.post(
        "/login",
        data={"username": "boss2", "password": "admin-password-123"},
        follow_redirects=False,
    )
    assert new_login.status_code == 303


def test_change_username_case_only_is_allowed(
    client: TestClient, settings: Settings
) -> None:
    admin = admin_client(settings)
    response = admin.post(
        "/admin/profile",
        data={
            "username": "ADMIN",
            "current_password": "admin-password-123",
            "csrf_token": admin.cookies.get("vic_csrf"),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_change_username_must_be_unique(
    client: TestClient, settings: Settings
) -> None:
    register(client, "alice")
    admin = admin_client(settings)
    response = admin.post(
        "/admin/profile",
        data={
            "username": "ALICE",
            "current_password": "admin-password-123",
            "csrf_token": admin.cookies.get("vic_csrf"),
        },
    )
    assert response.status_code == 400
    assert "already taken" in response.text

    connection = sqlite3.connect(settings.database_path)
    try:
        assert connection.execute(
            "SELECT COUNT(*) FROM users WHERE username = 'admin'"
        ).fetchone()[0] == 1
    finally:
        connection.close()


def test_change_password_invalidates_other_sessions(
    client: TestClient, settings: Settings
) -> None:
    admin_one = admin_client(settings)
    admin_two = admin_client(settings)
    response = admin_one.post(
        "/admin/profile",
        data={
            "username": "admin",
            "current_password": "admin-password-123",
            "new_password": "brand-new-admin-1",
            "confirm_password": "brand-new-admin-1",
            "csrf_token": admin_one.cookies.get("vic_csrf"),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    # Current session survives; the other session is signed out.
    assert admin_one.get("/").status_code == 200
    assert admin_two.get("/", follow_redirects=False).headers["location"] == "/login"

    old_login = client.post(
        "/login",
        data={"username": "admin", "password": "admin-password-123"},
        follow_redirects=False,
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/login",
        data={"username": "admin", "password": "brand-new-admin-1"},
        follow_redirects=False,
    )
    assert new_login.status_code == 303


def test_profile_wrong_current_password_changes_nothing(
    client: TestClient, settings: Settings
) -> None:
    admin = admin_client(settings)
    response = admin.post(
        "/admin/profile",
        data={
            "username": "boss2",
            "current_password": "wrong-password-1",
            "new_password": "brand-new-admin-1",
            "confirm_password": "brand-new-admin-1",
            "csrf_token": admin.cookies.get("vic_csrf"),
        },
    )
    assert response.status_code == 400
    assert "Current password is incorrect" in response.text

    verify = TestClient(create_app(settings))
    login = verify.post(
        "/login",
        data={"username": "admin", "password": "admin-password-123"},
        follow_redirects=False,
    )
    assert login.status_code == 303


def test_profile_password_confirmation_must_match(
    client: TestClient, settings: Settings
) -> None:
    admin = admin_client(settings)
    response = admin.post(
        "/admin/profile",
        data={
            "username": "admin",
            "current_password": "admin-password-123",
            "new_password": "brand-new-admin-1",
            "confirm_password": "different-admin-1",
            "csrf_token": admin.cookies.get("vic_csrf"),
        },
    )
    assert response.status_code == 400
    assert "do not match" in response.text


def test_profile_requires_csrf(client: TestClient, settings: Settings) -> None:
    admin = admin_client(settings)
    response = admin.post(
        "/admin/profile",
        data={"username": "boss2", "current_password": "admin-password-123"},
    )
    assert response.status_code == 403


def test_profile_no_changes_reports_nothing(
    client: TestClient, settings: Settings
) -> None:
    admin = admin_client(settings)
    response = admin.post(
        "/admin/profile",
        data={
            "username": "admin",
            "current_password": "admin-password-123",
            "csrf_token": admin.cookies.get("vic_csrf"),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/profile?saved=nothing"
