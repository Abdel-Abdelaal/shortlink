import json

import pytest
from fastapi import Request

from shortlink.api.errors import handle_domain_error
from shortlink.domain.errors import LinkNotFoundError, ShortlinkError


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/abc",
            "query_string": b"",
            "headers": [],
        }
    )


@pytest.mark.anyio
async def test_unregistered_error_falls_back_to_generic_problem() -> None:
    class UnregisteredError(ShortlinkError):
        pass

    response = await handle_domain_error(
        make_request(), UnregisteredError("sensitive message")
    )
    assert response.status_code == 500
    assert response.media_type == "application/problem+json"
    body = json.loads(bytes(response.body))
    assert body["title"] == "Internal error"
    assert body["detail"] == "The server could not complete the request."
    assert "sensitive message" not in bytes(response.body).decode()


@pytest.mark.anyio
async def test_registered_error_keeps_documented_mapping() -> None:
    response = await handle_domain_error(make_request(), LinkNotFoundError())
    assert response.status_code == 404
    assert response.media_type == "application/problem+json"
    body = json.loads(bytes(response.body))
    assert body["title"] == "Link not found"
    assert body["detail"] == "No link exists for that code."
