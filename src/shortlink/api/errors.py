"""Translate every failure to RFC 9457 problem details in one place."""

from collections.abc import Sequence
from http import HTTPStatus
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from shortlink.api.schemas import Problem
from shortlink.domain.errors import (
    CodeTakenError,
    InvalidCodeError,
    InvalidExpiryError,
    LinkExpiredError,
    LinkNotFoundError,
)

PROBLEM_MEDIA_TYPE = "application/problem+json"
VALIDATION_STATUS = 422
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


def problem(
    request: Request, status: int, title: str, detail: str, **extra: object
) -> JSONResponse:
    """Build one problem response; never includes database or stack details."""
    body = Problem(
        type="about:blank",
        title=title,
        status=status,
        detail=detail,
        instance=request.url.path,
        **extra,  # pyright: ignore[reportArgumentType]
    )
    return JSONResponse(
        status_code=status,
        media_type=PROBLEM_MEDIA_TYPE,
        content=body.model_dump(exclude_none=True),
    )


async def handle_domain_error(request: Request, error: Exception) -> JSONResponse:
    """Map a domain error to its documented status."""
    status, title, detail = PROBLEMS[type(error)]
    return problem(request, status, title, detail)


async def handle_validation_error(request: Request, error: Exception) -> JSONResponse:
    """Report malformed requests in the same problem format as domain errors."""
    details: Sequence[Any] = (
        error.errors() if isinstance(error, RequestValidationError) else []
    )
    errors = [
        {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
        for item in jsonable_encoder(details)
    ]
    return problem(
        request,
        VALIDATION_STATUS,
        "Invalid request",
        "The request did not match the documented schema.",
        errors=errors,
    )


async def handle_http_error(request: Request, error: Exception) -> JSONResponse:
    """Give framework errors (malformed body, unknown route) the same format."""
    if not isinstance(error, StarletteHTTPException):
        raise error
    title = HTTPStatus(error.status_code).phrase
    response = problem(request, error.status_code, title, str(error.detail))
    response.headers.update(error.headers or {})
    return response


def problem_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """Document problem responses so the OpenAPI schema matches what is returned."""
    schema = Problem.model_json_schema()
    return {
        status: {
            "description": "Problem details (RFC 9457)",
            "content": {PROBLEM_MEDIA_TYPE: {"schema": schema}},
        }
        for status in statuses
    }
