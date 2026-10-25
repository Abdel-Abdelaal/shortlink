"""Expose link operations over HTTP without embedding business policy."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Path, Request, Response, status
from fastapi.responses import RedirectResponse

from shortlink.api.errors import problem_responses
from shortlink.api.schemas import CreateLinkRequest, LinkResponse
from shortlink.domain.codes import CODE_PATTERN
from shortlink.domain.models import Link
from shortlink.domain.service import LinkService


def get_link_service(request: Request) -> LinkService:
    """Read the service wired by the application factory."""
    return cast(LinkService, request.app.state.link_service)


LinkServiceDependency = Annotated[LinkService, Depends(get_link_service)]
CodeParameter = Annotated[str, Path(pattern=CODE_PATTERN.pattern)]


def link_response(link: Link, base_url: str) -> LinkResponse:
    """Build public metadata using the configured origin rather than Host input."""
    return LinkResponse(
        code=link.code,
        short_url=f"{base_url.rstrip('/')}/{link.code}",
        target_url=link.target_url,
        created_at=link.created_at,
        expires_at=link.expires_at,
        hits=link.hits,
    )


def create_router(base_url: str) -> APIRouter:
    """Build routes with the configured public URL."""
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        """Report liveness for load balancers and deployment smoke tests."""
        return {"status": "ok"}

    @router.post(
        "/links",
        status_code=status.HTTP_201_CREATED,
        responses=problem_responses(400, 409, 422),
    )
    def create_link(
        body: CreateLinkRequest, response: Response, service: LinkServiceDependency
    ) -> LinkResponse:
        """Create a link and expose its stats resource in Location."""
        link = service.create(str(body.target_url), body.code, body.expires_at)
        response.headers["Location"] = f"/links/{link.code}"
        return link_response(link, base_url)

    @router.get("/links/{code}", responses=problem_responses(404, 422))
    def link_stats(code: CodeParameter, service: LinkServiceDependency) -> LinkResponse:
        """Read link metadata without incrementing hits."""
        return link_response(service.stats(code), base_url)

    @router.delete(
        "/links/{code}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses=problem_responses(404, 422),
    )
    def delete_link(code: CodeParameter, service: LinkServiceDependency) -> Response:
        """Remove a link from storage."""
        service.delete(code)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(
        "/{code}",
        status_code=307,
        response_class=RedirectResponse,
        responses=problem_responses(404, 410, 422),
    )
    def resolve_link(
        code: CodeParameter, service: LinkServiceDependency
    ) -> RedirectResponse:
        """Redirect to an active link and count the successful resolution."""
        return RedirectResponse(service.resolve(code).target_url, status_code=307)

    return router
