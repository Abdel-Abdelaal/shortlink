import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from shortlink.api.errors import handle_domain_error, handle_http_error
from shortlink.domain.errors import CodeTakenError, ShortlinkError
from shortlink.main import create_app
from shortlink.settings import Settings


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


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


@pytest.mark.anyio
async def test_subclass_of_registered_error_inherits_problem() -> None:
    class CustomCodeTakenError(CodeTakenError):
        pass

    request = Request({"type": "http", "path": "/", "headers": [], "method": "GET"})
    response = await handle_domain_error(request, CustomCodeTakenError())
    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    body = json.loads(bytes(response.body))
    assert body["title"] == "Code already exists"
    assert body["status"] == 409
    assert body["instance"] == "/"


@pytest.mark.anyio
async def test_unregistered_domain_error_falls_back_without_leaking() -> None:
    class UnexpectedError(ShortlinkError):
        pass

    request = Request({"type": "http", "path": "/", "headers": [], "method": "GET"})
    response = await handle_domain_error(request, UnexpectedError("secret db detail"))
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    raw = bytes(response.body)
    body = json.loads(raw)
    assert body["title"] == "Internal error"
    assert "secret db detail" not in raw.decode()
