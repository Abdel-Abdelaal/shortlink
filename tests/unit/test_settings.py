from pathlib import Path

import pytest
from pydantic import HttpUrl, ValidationError

from shortlink.settings import Settings

ENV_VARS = ("SHORTLINK_DATABASE_PATH", "SHORTLINK_BASE_URL", "SHORTLINK_CODE_LENGTH")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_defaults() -> None:
    settings = Settings()
    assert settings.database_path == Path("shortlink.db")
    assert settings.base_url == HttpUrl("http://127.0.0.1:8000")
    assert settings.code_length == 7


def test_database_path_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SHORTLINK_DATABASE_PATH", str(tmp_path / "x.db"))
    settings = Settings()
    assert settings.database_path == tmp_path / "x.db"
    assert settings.base_url == HttpUrl("http://127.0.0.1:8000")
    assert settings.code_length == 7


def test_base_url_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTLINK_BASE_URL", "https://short.example")
    settings = Settings()
    assert settings.base_url == HttpUrl("https://short.example")
    assert settings.database_path == Path("shortlink.db")
    assert settings.code_length == 7


def test_code_length_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORTLINK_CODE_LENGTH", "12")
    settings = Settings()
    assert settings.code_length == 12
    assert settings.database_path == Path("shortlink.db")
    assert settings.base_url == HttpUrl("http://127.0.0.1:8000")


@pytest.mark.parametrize("length", ["3", "33"])
def test_code_length_out_of_range_raises(
    length: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SHORTLINK_CODE_LENGTH", length)
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("length", ["4", "32"])
def test_code_length_boundaries_accepted(
    length: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SHORTLINK_CODE_LENGTH", length)
    assert Settings().code_length == int(length)
