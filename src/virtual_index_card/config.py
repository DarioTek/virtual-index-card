"""Runtime configuration loaded from environment variables.

A local ``.env`` file is read when present (see ``.env.example``). Real
environment variables always win over ``.env`` values so that systemd,
containers, and shells stay authoritative.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

DEFAULT_DATABASE_PATH = Path("data/virtual-index-card.sqlite3")
DEFAULT_SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
# Export limits bound both the API and the HTML form; see docs/architecture.md.
DEFAULT_MAX_EXPORT_ROWS = 10000
DEFAULT_MAX_EXPORT_BYTES = 1_048_576


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}.") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero, got {value}.")
    return value


@dataclass(frozen=True)
class Settings:
    database_path: Path
    session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS
    cookie_secure: bool = False
    # Interactive API docs (/docs, /redoc, /openapi.json). Off unless explicitly enabled.
    enable_docs: bool = False
    # Optional administrator bootstrap, applied on every startup:
    # ensures the account exists with the admin role and the given password.
    admin_username: str | None = None
    admin_password: str | None = None
    # Caps for the full-fidelity JSON export; both apply to every export.
    max_export_rows: int = field(default=DEFAULT_MAX_EXPORT_ROWS)
    max_export_bytes: int = field(default=DEFAULT_MAX_EXPORT_BYTES)


def load_settings(dotenv_path: Path | None = None) -> Settings:
    """Build Settings from the environment (optionally seeded from a .env file).

    With no explicit path, a ``.env`` in the current working directory is used.
    ``override=False`` keeps real environment variables authoritative.
    """
    if dotenv_path is not None:
        load_dotenv(dotenv_path=dotenv_path, override=False)
    else:
        load_dotenv(dotenv_path=find_dotenv(usecwd=True), override=False)
    database_path = Path(os.environ.get("VIC_DATABASE_PATH", str(DEFAULT_DATABASE_PATH)))
    return Settings(
        database_path=database_path,
        session_ttl_seconds=_env_int("VIC_SESSION_TTL_SECONDS", DEFAULT_SESSION_TTL_SECONDS),
        cookie_secure=_env_flag("VIC_COOKIE_SECURE"),
        enable_docs=_env_flag("VIC_ENABLE_DOCS"),
        admin_username=os.environ.get("VIC_ADMIN_USERNAME", "").strip() or None,
        admin_password=os.environ.get("VIC_ADMIN_PASSWORD") or None,
        max_export_rows=_env_int("VIC_MAX_EXPORT_ROWS", DEFAULT_MAX_EXPORT_ROWS),
        max_export_bytes=_env_int("VIC_MAX_EXPORT_BYTES", DEFAULT_MAX_EXPORT_BYTES),
    )
