"""Create or promote an administrator account.

Usage:
    uv run python -m virtual_index_card.create_admin USERNAME [--password PASSWORD]

Without --password: an existing account is promoted and its password is left
unchanged; a new account is created with a random temporary password that is
printed once.
"""

from __future__ import annotations

import argparse
from contextlib import closing

from . import repository as repo
from .admin import ensure_admin
from .config import load_settings
from .db import connect, initialize
from .security import generate_temporary_password


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("username", help="Administrator account name (created if missing).")
    parser.add_argument(
        "--password",
        default=None,
        help="Password to set. Generated and printed once when omitted for a new account.",
    )
    args = parser.parse_args()

    settings = load_settings()
    initialize(settings.database_path)
    generated = False
    with closing(connect(settings.database_path)) as connection:
        with connection:
            existing = repo.get_user_by_username(connection, args.username.strip())
            password = args.password
            if password is None and existing is None:
                password = generate_temporary_password()
                generated = True
            action = ensure_admin(connection, args.username, password)
    if action == "created":
        print(f"Administrator account {args.username!r} created.")
        if generated:
            print(f"Temporary password (shown once): {password}")
    elif action == "promoted-password-updated":
        print(f"User {args.username!r} promoted to administrator and password reset.")
    else:
        print(f"User {args.username!r} promoted to administrator.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
