"""Typed request and response data at the HTTP boundary."""

from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, HttpUrl


class CreateLinkRequest(BaseModel):
    """A validated HTTP target, optional code and optional aware expiry."""

    model_config = ConfigDict(extra="forbid")

    target_url: HttpUrl
    code: str | None = None
    expires_at: AwareDatetime | None = None


class LinkResponse(BaseModel):
    """Public link metadata, with a short URL derived from configured origin."""

    code: str
    short_url: str
    target_url: str
    created_at: datetime
    expires_at: datetime | None
    hits: int
