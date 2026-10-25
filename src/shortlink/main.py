"""Wire the HTTP application to storage and time adapters."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from shortlink.api.errors import (
    handle_domain_error,
    handle_http_error,
    handle_validation_error,
)
from shortlink.api.routes import create_router
from shortlink.db.sqlite import SqliteLinkRepository
from shortlink.domain.errors import ShortlinkError
from shortlink.domain.ports import SystemClock
from shortlink.domain.service import LinkService
from shortlink.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an isolated app, delaying database creation until its lifespan starts."""
    configured = settings if settings is not None else Settings()
    repository = SqliteLinkRepository(configured.database_path)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        """Initialize storage and bind one stateless service per application."""
        repository.initialize()
        application.state.link_service = LinkService(
            repository, SystemClock(), configured.code_length
        )
        yield

    application = FastAPI(title="shortlink", lifespan=lifespan)
    application.add_exception_handler(ShortlinkError, handle_domain_error)
    application.add_exception_handler(RequestValidationError, handle_validation_error)
    application.add_exception_handler(StarletteHTTPException, handle_http_error)
    application.include_router(create_router(str(configured.base_url)))
    return application


app = create_app()
