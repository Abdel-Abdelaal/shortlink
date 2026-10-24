"""Immutable link data shared by domain and adapters."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Link:
    """A short code and its redirect target with usage metadata."""

    code: str
    target_url: str
    created_at: datetime
    expires_at: datetime | None
    hits: int = 0
