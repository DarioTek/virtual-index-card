"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DATABASE_PATH = Path("data/virtual-index-card.sqlite3")
DEFAULT_SESSION_TTL_SECONDS = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class Settings:
    database_path: Path
    session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS
    cookie_secure: bool = False
    # Optional administrator bootstrap, applied on every startup:
    # ensures the account exists with the admin role and the given password.
    admin_username: str | None = None
    admin_password: str | None = None


def load_settings() -> Settings:
    database_path = Path(os.environ.get("VIC_DATABASE_PATH", str(DEFAULT_DATABASE_PATH)))
    ttl_raw = os.environ.get("VIC_SESSION_TTL_SECONDS", str(DEFAULT_SESSION_TTL_SECONDS))
    cookie_secure = os.environ.get("VIC_COOKIE_SECURE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return Settings(
        database_path=database_path,
        session_ttl_seconds=int(ttl_raw),
        cookie_secure=cookie_secure,
        admin_username=os.environ.get("VIC_ADMIN_USERNAME", "").strip() or None,
        admin_password=os.environ.get("VIC_ADMIN_PASSWORD") or None,
    )
