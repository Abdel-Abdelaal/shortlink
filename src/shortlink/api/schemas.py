"""Typed request and response data at the HTTP boundary."""

from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl

from shortlink.domain.codes import CODE_PATTERN


class CreateLinkRequest(BaseModel):
    """A validated HTTP target, optional code and optional aware expiry."""

    model_config = ConfigDict(extra="forbid")

    target_url: HttpUrl
    code: str | None = Field(default=None, pattern=CODE_PATTERN.pattern)
    expires_at: AwareDatetime | None = None


class Problem(BaseModel):
    """An RFC 9457 problem details body, used for every error response."""

    type: str
    title: str
    status: int
    detail: str
    instance: str
    errors: list[dict[str, object]] | None = None


class LinkResponse(BaseModel):
    """Public link metadata, with a short URL derived from configured origin."""

    code: str
    short_url: str
    target_url: str
    created_at: datetime
    expires_at: datetime | None
    hits: int
