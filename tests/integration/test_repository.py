from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest

from shortlink.db.sqlite import SqliteLinkRepository
from shortlink.domain.errors import LinkNotFoundError
from shortlink.domain.models import Link


def test_concurrent_hits_are_not_lost(tmp_path: Path) -> None:
    repository = SqliteLinkRepository(tmp_path / "concurrent.db")
    repository.initialize()
    repository.add(Link("count123", "https://example.com", datetime.now(UTC), None))
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(repository.increment_hits, ["count123"] * 40))
    assert repository.get("count123").hits == 40


def test_missing_hit_increment_is_not_silently_ignored(tmp_path: Path) -> None:
    repository = SqliteLinkRepository(tmp_path / "links.db")
    repository.initialize()
    with pytest.raises(LinkNotFoundError):
        repository.increment_hits("missing1")
