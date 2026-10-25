"""Generate API tests from the OpenAPI schema that FastAPI publishes."""

# Schemathesis exposes partially typed callables; strict mode can't infer them.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportUnknownParameterType=false
# pyright: reportMissingTypeArgument=false, reportUntypedFunctionDecorator=false

from collections.abc import Iterator
from pathlib import Path

import pytest
import schemathesis
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, assume, settings
from pydantic import HttpUrl
from schemathesis import Case
from schemathesis.specs.openapi.checks import (
    allow_header_conformance,
    positive_data_acceptance,
)
from schemathesis.specs.openapi.schemas import OpenApiSchema

from shortlink.domain.codes import RESERVED_CODES
from shortlink.main import create_app
from shortlink.settings import Settings

# Checks that can't pass for reasons outside the published schema:
# - positive_data_acceptance: "expires_at must be in the future" is a business
#   rule JSON Schema cannot express, so some schema-valid bodies get a 422.
# - allow_header_conformance: Starlette's 405 for an unsupported method lists only
#   the first matching route's methods in Allow; not something the app controls.
EXCLUDED_CHECKS = [positive_data_acceptance, allow_header_conformance]


@pytest.fixture
def api_schema(tmp_path: Path) -> Iterator[OpenApiSchema]:
    """Serve a fresh app and database, with its lifespan running."""
    app = create_app(
        Settings(
            database_path=tmp_path / "links.db",
            base_url=HttpUrl("https://short.example"),
        )
    )
    with TestClient(app):
        yield schemathesis.openapi.from_asgi("/openapi.json", app)


schema = schemathesis.pytest.from_fixture("api_schema")


@schema.parametrize()
@settings(
    max_examples=50,
    derandomize=True,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_every_response_matches_the_published_schema(case: Case) -> None:
    # Reserved codes are application routes (e.g. /docs), by design.
    assume((case.path_parameters or {}).get("code") not in RESERVED_CODES)
    case.call_and_validate(excluded_checks=EXCLUDED_CHECKS)
