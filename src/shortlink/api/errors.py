"""Translate domain failures to RFC 9457 problem details in one place."""

from fastapi import Request
from fastapi.responses import JSONResponse

from shortlink.domain.errors import (
    CodeTakenError,
    InvalidCodeError,
    InvalidExpiryError,
    LinkExpiredError,
    LinkNotFoundError,
)

PROBLEMS: dict[type[Exception], tuple[int, str, str]] = {
    LinkNotFoundError: (404, "Link not found", "No link exists for that code."),
    LinkExpiredError: (410, "Link expired", "The link has reached its expiry time."),
    CodeTakenError: (409, "Code already exists", "Choose another short code."),
    InvalidCodeError: (
        422,
        "Invalid code",
        "Use 4-32 letters, digits, underscores or hyphens; route names are reserved.",
    ),
    InvalidExpiryError: (
        422,
        "Invalid expiry",
        "Expiry must be timezone-aware and in the future.",
    ),
}


async def handle_domain_error(request: Request, error: Exception) -> JSONResponse:
    """Return a stable problem response without leaking database details."""
    status, title, detail = PROBLEMS[type(error)]
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.url.path,
        },
    )
