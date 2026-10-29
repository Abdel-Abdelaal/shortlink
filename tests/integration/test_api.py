import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from shortlink.api.errors import handle_http_error
from shortlink.main import create_app
from shortlink.settings import Settings


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_head_health_matches_get_without_body(client: TestClient) -> None:
    head = client.head("/health")
    get = client.get("/health")
    assert head.status_code == 200
    assert head.content == b""
    assert head.headers["content-type"] == get.headers["content-type"]


def test_create_redirect_stats_delete(client: TestClient) -> None:
    response = client.post(
        "/links", json={"target_url": "https://example.com/path", "code": "custom_1"}
    )
    assert response.status_code == 201
    assert response.headers["location"] == "/links/custom_1"
    link = response.json()
    assert link["short_url"] == "https://short.example/custom_1"
    assert link["hits"] == 0
    assert link["expires_at"] is None
    redirect = client.get("/custom_1", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "https://example.com/path"
    assert client.get("/links/custom_1").json()["hits"] == 1
    assert client.delete("/links/custom_1").status_code == 204
    assert client.get("/custom_1").status_code == 404


def test_generated_link_has_seven_character_code(client: TestClient) -> None:
    response = client.post("/links", json={"target_url": "https://example.com"})
    assert response.status_code == 201
    assert len(response.json()["code"]) == 7


def test_head_preview_does_not_count_hits(client: TestClient) -> None:
    client.post(
        "/links",
        json={"target_url": "https://example.com/a*b", "code": "preview1"},
    )
    first = client.head("/preview1", follow_redirects=False)
    second = client.head("/preview1", follow_redirects=False)
    for head in (first, second):
        assert head.status_code == 307
        assert head.content == b""
    assert client.get("/links/preview1").json()["hits"] == 0
    redirect = client.get("/preview1", follow_redirects=False)
    assert redirect.status_code == 307
    assert first.headers["location"] == redirect.headers["location"]
    assert second.headers["location"] == redirect.headers["location"]
    assert client.get("/links/preview1").json()["hits"] == 1


def test_duplicate_returns_problem_without_overwriting(client: TestClient) -> None:
    body = {"target_url": "https://example.com/first", "code": "duplicate"}
    assert client.post("/links", json=body).status_code == 201
    response = client.post(
        "/links", json={**body, "target_url": "https://example.com/second"}
    )
    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "about:blank"
    assert client.get("/links/duplicate").json()["target_url"] == body["target_url"]


@pytest.mark.parametrize(
    "target_url",
    ["javascript:alert(1)", "file:///etc/passwd", "ftp://example.com", "not a URL"],
)
def test_non_http_targets_are_rejected(client: TestClient, target_url: str) -> None:
    assert client.post("/links", json={"target_url": target_url}).status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {"target_url": "https://example.com", "code": "abc"},
        {"target_url": "https://example.com", "code": "health"},
        {"target_url": "https://example.com", "expires_at": "2000-01-01T00:00:00Z"},
        {"target_url": "https://example.com", "expires_at": "2099-01-01T00:00:00"},
        {"target_url": "https://example.com", "unknown": True},
    ],
)
def test_invalid_input_returns_422(
    client: TestClient, body: dict[str, str | bool]
) -> None:
    assert client.post("/links", json=body).status_code == 422


@pytest.mark.parametrize("path", ["/missing1", "/links/missing1"])
def test_missing_link_problem(client: TestClient, path: str) -> None:
    response = client.get(path, follow_redirects=False)
    assert response.status_code == 404
    assert response.json()["status"] == 404
    assert response.json()["instance"] == path


def test_deleting_unknown_link_returns_404(client: TestClient) -> None:
    assert client.delete("/links/missing1").status_code == 404


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [("/missing1", 404), ("/ab", 422)],
)
def test_head_errors_are_empty_problems(
    client: TestClient, path: str, expected_status: int
) -> None:
    response = client.head(path, follow_redirects=False)
    assert response.status_code == expected_status
    assert response.content == b""
    assert response.headers["content-type"] == "application/problem+json"


def test_expired_redirect_returns_410(client: TestClient, tmp_path: Path) -> None:
    # Seed the real database after creation so the API test needs no sleep.

    expires_at = datetime.now(UTC) + timedelta(days=1)
    response = client.post(
        "/links",
        json={
            "target_url": "https://example.com",
            "code": "expired1",
            "expires_at": expires_at.isoformat(),
        },
    )
    assert response.status_code == 201
    with closing(sqlite3.connect(tmp_path / "links.db")) as connection, connection:
        connection.execute(
            "UPDATE links SET expires_at = ? WHERE code = ?",
            ("2000-01-01T00:00:00+00:00", "expired1"),
        )
    response = client.get("/expired1", follow_redirects=False)
    assert response.status_code == 410
    assert response.json()["title"] == "Link expired"
    assert client.get("/links/expired1").json()["hits"] == 0


def test_head_expired_link_returns_empty_410(
    client: TestClient, tmp_path: Path
) -> None:
    expires_at = datetime.now(UTC) + timedelta(days=1)
    response = client.post(
        "/links",
        json={
            "target_url": "https://example.com",
            "code": "expired1",
            "expires_at": expires_at.isoformat(),
        },
    )
    assert response.status_code == 201
    with closing(sqlite3.connect(tmp_path / "links.db")) as connection, connection:
        connection.execute(
            "UPDATE links SET expires_at = ? WHERE code = ?",
            ("2000-01-01T00:00:00+00:00", "expired1"),
        )
    head = client.head("/expired1", follow_redirects=False)
    assert head.status_code == 410
    assert head.content == b""
    assert head.headers["content-type"] == "application/problem+json"
    stats = client.get("/links/expired1")
    assert stats.status_code == 200
    assert stats.json()["hits"] == 0


def test_link_persists_across_app_instances(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "persistent.db")
    with TestClient(create_app(settings)) as first:
        assert (
            first.post(
                "/links", json={"target_url": "https://example.com", "code": "persist1"}
            ).status_code
            == 201
        )
    with TestClient(create_app(settings)) as second:
        assert second.get("/persist1", follow_redirects=False).status_code == 307


def test_malformed_body_is_a_documented_problem(client: TestClient) -> None:
    response = client.post(
        "/links",
        content=b"\xff\xfe not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code in {400, 422}
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["status"] == response.status_code


def test_validation_errors_use_the_problem_format(client: TestClient) -> None:
    response = client.post("/links", json={"target_url": "not a url"})
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["title"] == "Invalid request"
    assert body["errors"][0]["loc"] == ["body", "target_url"]


def test_unknown_route_uses_the_problem_format(client: TestClient) -> None:
    response = client.get("/links/abc123/extra")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.anyio
async def test_http_handler_rejects_non_http_errors() -> None:
    request = Request({"type": "http", "path": "/", "headers": [], "method": "GET"})
    with pytest.raises(ValueError, match="boom"):
        await handle_http_error(request, ValueError("boom"))


@pytest.mark.parametrize("path", ["/health", "/missing_1", "/abc"])
def test_head_content_length_matches_get(client: TestClient, path: str) -> None:
    get = client.get(path, follow_redirects=False)
    head = client.head(path, follow_redirects=False)
    assert head.status_code == get.status_code
    assert head.content == b""
    assert int(head.headers["content-length"]) == len(get.content)


@pytest.mark.parametrize(
    "target_url", ["https://example.com/a|b?q={x}", "https://example.com/a^b"]
)
def test_head_redirect_encoding_matches_get(
    client: TestClient, target_url: str
) -> None:
    created = client.post("/links", json={"target_url": target_url, "code": "encode_1"})
    assert created.status_code == 201
    head = client.head("/encode_1", follow_redirects=False)
    assert client.get("/links/encode_1").json()["hits"] == 0
    get = client.get("/encode_1", follow_redirects=False)
    assert head.status_code == get.status_code == 307
    assert head.headers["location"] == get.headers["location"]


@pytest.mark.anyio
@pytest.mark.parametrize("status", [499, 599])
@pytest.mark.parametrize("method", ["GET", "HEAD"])
async def test_http_handler_keeps_nonstandard_status(status: int, method: str) -> None:
    request = Request({"type": "http", "path": "/", "headers": [], "method": method})
    response = await handle_http_error(
        request,
        StarletteHTTPException(
            status, detail="Custom error", headers={"x-custom": "1"}
        ),
    )
    assert response.status_code == status
    assert response.media_type == "application/problem+json"
    assert response.headers["x-custom"] == "1"
    if method == "HEAD":
        assert bytes(response.body) == b""
    else:
        body = json.loads(bytes(response.body))
        assert body["status"] == status
        assert body["detail"] == "Custom error"
        assert body["title"] == "Error"


@pytest.mark.anyio
async def test_http_handler_keeps_standard_status_title() -> None:
    request = Request({"type": "http", "path": "/", "headers": [], "method": "GET"})
    response = await handle_http_error(
        request, StarletteHTTPException(404, detail="Not Found")
    )
    body = json.loads(bytes(response.body))
    assert body["title"] == "Not Found"
    assert body["status"] == 404
