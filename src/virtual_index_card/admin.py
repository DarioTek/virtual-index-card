"""Administrator bootstrap helpers shared by the CLI and app startup."""

from __future__ import annotations

import sqlite3

from . import repository as repo
from .domain import utc_now, validate_username
from .security import hash_password


def ensure_admin(
    connection: sqlite3.Connection,
    username: str,
    password: str | None,
) -> str:
    """Create or promote an administrator; optionally set their password.

    Returns one of: ``created``, ``promoted``, ``promoted-password-updated``.
    Raises ValueError when the user does not exist and no password is given.
    """
    username = username.strip()
    error = validate_username(username)
    if error is not None:
        raise ValueError(error)
    user = repo.get_user_by_username(connection, username)
    now = utc_now()
    if user is not None:
        repo.set_user_role(connection, int(user["id"]), "admin")
        if password is not None:
            salt, digest = hash_password(password)
            repo.set_user_password(connection, int(user["id"]), salt, digest)
            return "promoted-password-updated"
        return "promoted"
    if password is None:
        raise ValueError(
            f"User {username!r} does not exist; provide a password to create "
            "the administrator account."
        )
    salt, digest = hash_password(password)
    repo.create_user(connection, username, salt, digest, now, role="admin")
    return "created"
