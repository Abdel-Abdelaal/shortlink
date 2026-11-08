"""Preserve representation metadata when producing bodyless HEAD responses."""

from fastapi.responses import Response


def head_response(response: Response) -> Response:
    """Remove the body while preserving GET headers, including duplicate fields."""
    empty = Response(
        status_code=response.status_code,
        media_type=response.media_type,
        background=response.background,
    )
    empty.raw_headers = list(response.raw_headers)
    return empty
