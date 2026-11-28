"""Configuration loading, including optional .env support."""

from __future__ import annotations

import pytest

from virtual_index_card.config import (
    DEFAULT_MAX_EXPORT_BYTES,
    DEFAULT_MAX_EXPORT_ROWS,
    DEFAULT_SESSION_TTL_SECONDS,
    load_settings,
)

VIC_VARIABLES = (
    "VIC_DATABASE_PATH",
    "VIC_SESSION_TTL_SECONDS",
    "VIC_COOKIE_SECURE",
    "VIC_ENABLE_DOCS",
    "VIC_ADMIN_USERNAME",
    "VIC_ADMIN_PASSWORD",
    "VIC_MAX_EXPORT_ROWS",
    "VIC_MAX_EXPORT_BYTES",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch, tmp_path):
    """Isolate every test from the developer's shell and working-directory .env."""
    for name in VIC_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    # load_settings() searches the CWD when no path is given; keep that out of play.
    monkeypatch.chdir(tmp_path)
    yield


def test_defaults_match_documented_configuration() -> None:
    settings = load_settings()
    assert settings.session_ttl_seconds == DEFAULT_SESSION_TTL_SECONDS == 604800
    assert settings.cookie_secure is False
    assert settings.enable_docs is False
    assert settings.admin_username is None
    assert settings.admin_password is None
    assert settings.max_export_rows == DEFAULT_MAX_EXPORT_ROWS
    assert settings.max_export_bytes == DEFAULT_MAX_EXPORT_BYTES


def test_dotenv_values_are_loaded(tmp_path) -> None:
    env_file = tmp_path / "custom.env"
    env_file.write_text(
        "VIC_SESSION_TTL_SECONDS=120\n"
        "VIC_COOKIE_SECURE=true\n"
        "VIC_ENABLE_DOCS=yes\n"
        "VIC_ADMIN_USERNAME=admin\n"
        "VIC_MAX_EXPORT_ROWS=25\n",
        encoding="utf-8",
    )
    settings = load_settings(dotenv_path=env_file)
    assert settings.session_ttl_seconds == 120
    assert settings.cookie_secure is True
    assert settings.enable_docs is True
    assert settings.admin_username == "admin"
    assert settings.max_export_rows == 25


def test_real_environment_wins_over_dotenv(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / "custom.env"
    env_file.write_text("VIC_SESSION_TTL_SECONDS=120\n", encoding="utf-8")
    monkeypatch.setenv("VIC_SESSION_TTL_SECONDS", "999")
    assert load_settings(dotenv_path=env_file).session_ttl_seconds == 999


def test_repository_dotenv_file_is_picked_up(tmp_path, monkeypatch) -> None:
    """A .env in the working directory is read when no explicit path is given."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("VIC_ENABLE_DOCS=true\n", encoding="utf-8")
    assert load_settings().enable_docs is True


def test_invalid_integer_configuration_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("VIC_SESSION_TTL_SECONDS", "not-a-number")
    with pytest.raises(ValueError, match="VIC_SESSION_TTL_SECONDS"):
        load_settings()
    monkeypatch.setenv("VIC_SESSION_TTL_SECONDS", "0")
    with pytest.raises(ValueError, match="greater than zero"):
        load_settings()
