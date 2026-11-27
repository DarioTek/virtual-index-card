"""Password hashing, session tokens, and CSRF token helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets

PBKDF2_ITERATIONS = 200_000
SALT_BYTES = 16

# Unambiguous alphabet (no O/0, I/1/l) for human-transcribed temporary passwords.
TEMP_PASSWORD_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
TEMP_PASSWORD_LENGTH = 12


def hash_password(password: str) -> tuple[str, str]:
    """Return (salt_hex, hash_hex) for a new password."""
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, expected_hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    ).hex()
    return hmac.compare_digest(actual, expected_hash_hex)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def generate_temporary_password(length: int = TEMP_PASSWORD_LENGTH) -> str:
    """Return a random, human-readable temporary password (3 groups of 4)."""
    groups = []
    for _ in range(3):
        group_length = max(1, length // 3)
        groups.append(
            "".join(secrets.choice(TEMP_PASSWORD_ALPHABET) for _ in range(group_length))
        )
    return "-".join(groups)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(first: str | None, second: str | None) -> bool:
    if first is None or second is None:
        return False
    return hmac.compare_digest(first, second)
