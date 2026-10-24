"""Ports keep business rules independent of storage and wall time."""

from datetime import UTC, datetime
from typing import Protocol

from shortlink.domain.models import Link


class LinkRepository(Protocol):
    """Persistent storage operations required by the link service."""

    def add(self, link: Link) -> None:
        """Store a link, raising CodeTakenError for duplicate codes."""
        ...

    def get(self, code: str) -> Link:
        """Fetch a link, raising LinkNotFoundError if absent."""
        ...

    def increment_hits(self, code: str) -> None:
        """Atomically increment usage for an existing link."""
        ...

    def delete(self, code: str) -> None:
        """Remove a link, raising LinkNotFoundError if absent."""
        ...


class Clock(Protocol):
    """A source of timezone-aware UTC instants."""

    def now(self) -> datetime:
        """Return the current instant."""
        ...


class SystemClock:
    """Use the operating system's UTC clock in production."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC time."""
        return datetime.now(UTC)
