from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from shortlink.domain.codes import generate_code, validate_code
from shortlink.domain.errors import (
    CodeTakenError,
    InvalidCodeError,
    InvalidExpiryError,
    LinkExpiredError,
    LinkNotFoundError,
)
from shortlink.domain.models import Link
from shortlink.domain.service import MAX_CODE_ATTEMPTS, LinkService

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
TARGET_URL = "https://example.com/target"


@dataclass
class FixedClock:
    current: datetime = NOW

    def now(self) -> datetime:
        return self.current


class FakeRepository:
    def __init__(self) -> None:
        self.links: dict[str, Link] = {}

    def add(self, link: Link) -> None:
        if link.code in self.links:
            raise CodeTakenError
        self.links[link.code] = link

    def get(self, code: str) -> Link:
        try:
            return self.links[code]
        except KeyError as error:
            raise LinkNotFoundError from error

    def increment_hits(self, code: str) -> None:
        link = self.get(code)
        self.links[code] = replace(link, hits=link.hits + 1)

    def delete(self, code: str) -> None:
        self.get(code)
        del self.links[code]


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def service(clock: FixedClock) -> LinkService:
    return LinkService(FakeRepository(), clock)


def test_create_resolve_stats_and_delete(service: LinkService) -> None:
    link = service.create(TARGET_URL, "custom_1")
    assert link.created_at == NOW
    assert link.hits == 0
    assert service.resolve(link.code).target_url == TARGET_URL
    assert service.stats(link.code).hits == 1
    assert service.stats(link.code).hits == 1
    service.delete(link.code)
    with pytest.raises(LinkNotFoundError):
        service.stats(link.code)


def test_duplicate_custom_code_does_not_overwrite(service: LinkService) -> None:
    service.create(TARGET_URL, "custom_1")
    with pytest.raises(CodeTakenError):
        service.create("https://other.example", "custom_1")
    assert service.stats("custom_1").target_url == TARGET_URL


@pytest.mark.parametrize(
    "code",
    [
        "abc",
        "a" * 33,
        "has space",
        "sql'--",
        "health",
        "docs",
        "redoc",
        "links",
        "cafÃ©",
    ],
)
def test_invalid_or_reserved_code_is_rejected(code: str) -> None:
    with pytest.raises(InvalidCodeError):
        validate_code(code)


@pytest.mark.parametrize("code", ["abcd", "a" * 32, "Ab12_-cd"])
def test_valid_custom_codes(code: str) -> None:
    validate_code(code)


@pytest.mark.parametrize("length", [0, 3, 33])
def test_invalid_generated_length(length: int) -> None:
    with pytest.raises(InvalidCodeError):
        generate_code(length)


def test_generated_code_is_base62() -> None:
    code = generate_code(7)
    assert len(code) == 7
    assert code.isascii()
    assert code.isalnum()


@pytest.mark.parametrize(
    "expiry", [NOW - timedelta(seconds=1), NOW, NOW.replace(tzinfo=None)]
)
def test_invalid_expiry_is_rejected(service: LinkService, expiry: datetime) -> None:
    with pytest.raises(InvalidExpiryError):
        service.create(TARGET_URL, expires_at=expiry)


def test_expiry_boundary_does_not_count_failed_redirect(
    service: LinkService, clock: FixedClock
) -> None:
    expires_at = NOW + timedelta(seconds=10)
    link = service.create(TARGET_URL, "expiry1", expires_at)
    clock.current = expires_at - timedelta(microseconds=1)
    service.resolve(link.code)
    clock.current = expires_at
    with pytest.raises(LinkExpiredError):
        service.resolve(link.code)
    assert service.stats(link.code).hits == 1


def test_generated_collision_retries(
    service: LinkService, monkeypatch: pytest.MonkeyPatch
) -> None:
    service.create(TARGET_URL, "taken12")
    generate = Mock(side_effect=["taken12", "fresh12"])
    monkeypatch.setattr("shortlink.domain.service.generate_code", generate)
    assert service.create(TARGET_URL).code == "fresh12"
    assert generate.call_count == 2


def test_generated_reserved_code_retries(
    service: LinkService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "shortlink.domain.service.generate_code",
        Mock(side_effect=["health", "fresh12"]),
    )
    assert service.create(TARGET_URL).code == "fresh12"


def test_generated_collision_retries_are_bounded(
    service: LinkService, monkeypatch: pytest.MonkeyPatch
) -> None:
    service.create(TARGET_URL, "taken12")
    generate = Mock(return_value="taken12")
    monkeypatch.setattr("shortlink.domain.service.generate_code", generate)
    with pytest.raises(CodeTakenError):
        service.create(TARGET_URL)
    assert generate.call_count == MAX_CODE_ATTEMPTS


def test_unknown_code_cannot_resolve(service: LinkService) -> None:
    with pytest.raises(LinkNotFoundError):
        service.resolve("missing1")
