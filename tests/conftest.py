from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import HttpUrl

from shortlink.main import create_app
from shortlink.settings import Settings


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        database_path=tmp_path / "links.db", base_url=HttpUrl("https://short.example")
    )
    with TestClient(create_app(settings)) as client:
        yield client
