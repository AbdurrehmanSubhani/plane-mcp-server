from __future__ import annotations

import contextlib
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .auth import (
    PlaneAuthError,
    get_auth_context,
    reset_current_auth,
    resolve_http_auth,
    set_current_auth,
)
from .client import PlaneAPIClient, PlaneAPIError
from .config import ServerSettings


def create_mcp(settings: ServerSettings) -> FastMCP:
    mcp = FastMCP(
        settings.server_name,
        instructions=(
            "Plane MCP server for current Plane APIs. "
            "Use current work item endpoints first. "
            "For HTTP deployments, authenticate with Authorization: Bearer <PLANE_API_KEY> "
            "and X-Workspace-Slug."
        ),
        stateless_http=True,
        json_response=True,
    )

    @mcp.tool()
    async def health() -> dict[str, Any]:
        """Return server health and configuration summary."""
        return {
            "status": "ok",
            "default_base_url": settings.default_base_url,
            "allowed_base_urls": list(settings.allowed_base_urls),
            "allow_mutations": settings.allow_mutations,
        }

    @mcp.tool()
    async def get_current_user() -> Any:
        """Get the current authenticated Plane user."""
        return await _request(settings, "GET", "/v1/users/me/")

    @mcp.tool()
    async def list_projects(
        cursor: str | None = None,
        per_page: int | None = 50,
        order_by: str | None = None,
    ) -> Any:
        """List Plane projects for the current workspace."""
        return await _request(
            settings,
            "GET",
            "/v1/projects/",
            params={"cursor": cursor, "per_page": per_page, "order_by": order_by},
        )

    @mcp.tool()
    async def retrieve_project(project_id: str) -> Any:
        """Retrieve a Plane project by UUID."""
        return await _request(settings, "GET", f"/v1/projects/{project_id}/")

    @mcp.tool()
    async def list_states(project_id: str) -> Any:
        """List states in a Plane project."""
        return await _request(settings, "GET", f"/v1/projects/{project_id}/states/")

    @mcp.tool()
    async def list_cycles(project_id: str) -> Any:
        """List cycles in a Plane project."""
        return await _request(settings, "GET", f"/v1/projects/{project_id}/cycles/")

    @mcp.tool()
    async def list_modules(project_id: str) -> Any:
        """List modules in a Plane project."""
        return await _request(settings, "GET", f"/v1/projects/{project_id}/modules/")

    @mcp.tool()
    async def list_labels(project_id: str) -> Any:
        """List labels in a Plane project."""
        return await _request(settings, "GET", f"/v1/projects/{project_id}/labels/")

    @mcp.tool()
    async def list_work_item_types(project_id: str) -> Any:
        """List work item types in a Plane project."""
        return await _request(settings, "GET", f"/v1/projects/{project_id}/work-item-types/")

    @mcp.tool()
    async def list_work_items(
        project_id: str | None = None,
        query: str | None = None,
        state_ids: list[str] | None = None,
        priorities: list[str] | None = None,
        label_ids: list[str] | None = None,
        cycle_ids: list[str] | None = None,
        module_ids: list[str] | None = None,
        assignee_ids: list[str] | None = None,
        type_ids: list[str] | None = None,
        limit: int | None = 25,
    ) -> Any:
        """List or search work items in the current workspace."""
        path = f"/v1/projects/{project_id}/work-items/" if project_id else "/v1/work-items/"
        params = {
            "query": query,
            "limit": limit,
            "state_ids": _csv(state_ids),
            "priorities": _csv(priorities),
            "label_ids": _csv(label_ids),
            "cycle_ids": _csv(cycle_ids),
            "module_ids": _csv(module_ids),
            "assignee_ids": _csv(assignee_ids),
            "type_ids": _csv(type_ids),
        }
        return await _request(settings, "GET", path, params=params)

    @mcp.tool()
    async def retrieve_work_item(project_id: str, work_item_id: str, expand: str | None = None) -> Any:
        """Retrieve a work item by project UUID and work item UUID."""
        return await _request(
            settings,
            "GET",
            f"/v1/projects/{project_id}/work-items/{work_item_id}/",
            params={"expand": expand},
        )

    @mcp.tool()
    async def retrieve_work_item_by_identifier(identifier: str, expand: str | None = None) -> Any:
        """Retrieve a work item by readable identifier such as ENG-123."""
        return await _request(
            settings,
            "GET",
            f"/v1/work-items/{identifier}/",
            params={"expand": expand},
        )

    @mcp.tool()
    async def create_work_item(
        project_id: str,
        name: str,
        description_html: str | None = None,
        priority: str | None = None,
        state: str | None = None,
        assignees: list[str] | None = None,
        labels: list[str] | None = None,
        type_id: str | None = None,
        start_date: str | None = None,
        target_date: str | None = None,
    ) -> Any:
        """Create a new Plane work item."""
        payload = {
            "name": name,
            "description_html": description_html,
            "priority": priority,
            "state": state,
            "assignees": assignees,
            "labels": labels,
            "type_id": type_id,
            "start_date": start_date,
            "target_date": target_date,
        }
        return await _request(
            settings,
            "POST",
            f"/v1/projects/{project_id}/work-items/",
            json_body=payload,
            allow_mutation=True,
        )

    @mcp.tool()
    async def update_work_item(
        project_id: str,
        work_item_id: str,
        name: str | None = None,
        description_html: str | None = None,
        priority: str | None = None,
        state: str | None = None,
        assignees: list[str] | None = None,
        labels: list[str] | None = None,
        start_date: str | None = None,
        target_date: str | None = None,
    ) -> Any:
        """Update an existing Plane work item."""
        payload = {
            "name": name,
            "description_html": description_html,
            "priority": priority,
            "state": state,
            "assignees": assignees,
            "labels": labels,
            "start_date": start_date,
            "target_date": target_date,
        }
        return await _request(
            settings,
            "PATCH",
            f"/v1/projects/{project_id}/work-items/{work_item_id}/",
            json_body=payload,
            allow_mutation=True,
        )

    @mcp.tool()
    async def list_work_item_comments(project_id: str, work_item_id: str) -> Any:
        """List comments for a work item."""
        return await _request(
            settings,
            "GET",
            f"/v1/projects/{project_id}/work-items/{work_item_id}/comments/",
        )

    @mcp.tool()
    async def list_work_item_relations(project_id: str, work_item_id: str) -> Any:
        """List relations for a work item."""
        return await _request(
            settings,
            "GET",
            f"/v1/projects/{project_id}/work-items/{work_item_id}/relations/",
        )

    @mcp.tool()
    async def create_work_item_comment(project_id: str, work_item_id: str, comment_html: str) -> Any:
        """Create a comment on a work item."""
        return await _request(
            settings,
            "POST",
            f"/v1/projects/{project_id}/work-items/{work_item_id}/comments/",
            json_body={"comment_html": comment_html},
            allow_mutation=True,
        )

    @mcp.tool()
    async def create_work_log(
        project_id: str,
        work_item_id: str,
        duration: int,
        description: str | None = None,
    ) -> Any:
        """Create a work log entry on a work item."""
        return await _request(
            settings,
            "POST",
            f"/v1/projects/{project_id}/work-items/{work_item_id}/worklogs/",
            json_body={"duration": duration, "description": description},
            allow_mutation=True,
        )

    @mcp.tool()
    async def plane_api_request(
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        """Call a current Plane API path directly for newer endpoints not yet wrapped as typed tools."""
        validated_path = _validate_generic_path(path)
        allow_mutation = method.upper() in {"POST", "PUT", "PATCH", "DELETE"}
        return await _request(
            settings,
            method,
            validated_path,
            params=query,
            json_body=body,
            allow_mutation=allow_mutation,
        )

    return mcp


def create_http_app(settings: ServerSettings) -> Starlette:
    mcp = create_mcp(settings)
    mcp_app = mcp.streamable_http_app()
    app = Starlette(
        routes=[
            Route("/healthz", endpoint=_healthz),
            Mount("/", app=mcp_app),
        ],
        lifespan=_lifespan(mcp),
    )
    app.add_middleware(PublicHostRewriteMiddleware, settings=settings)
    app.add_middleware(PlaneAuthMiddleware, settings=settings)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Workspace-Slug", "X-Plane-Base-Url"],
            expose_headers=["Mcp-Session-Id"],
        )
    return app


async def _healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def _lifespan(mcp: FastMCP):
    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with mcp.session_manager.run():
            yield

    return lifespan


class PlaneAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: ServerSettings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        token = None
        try:
            if request.method != "OPTIONS" and request.url.path.startswith("/mcp"):
                auth = resolve_http_auth(request.headers, self.settings)
                token = set_current_auth(auth)
            response = await call_next(request)
            return response
        except PlaneAuthError as exc:
            return JSONResponse({"error": "authentication_required", "message": str(exc)}, status_code=401)
        finally:
            if token is not None:
                reset_current_auth(token)


class PublicHostRewriteMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: ServerSettings):
        super().__init__(app)
        self.settings = settings
        self.trusted_host = settings.trusted_mcp_host.encode("latin-1")

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/mcp"):
            request.scope["headers"] = _rewrite_host_header(request.scope["headers"], self.trusted_host)
        return await call_next(request)


async def _request(
    settings: ServerSettings,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    allow_mutation: bool = False,
) -> Any:
    auth = get_auth_context(settings)
    client = PlaneAPIClient(settings, auth)
    try:
        return await client.request(
            method,
            _workspace_path(auth.workspace_slug, path),
            params=params,
            json_body=json_body,
            allow_mutation=allow_mutation,
        )
    except PlaneAPIError as exc:
        return {
            "ok": False,
            "status_code": exc.status_code,
            "error": str(exc),
            "detail": exc.detail,
        }


def _workspace_path(workspace_slug: str, path: str) -> str:
    if path.startswith("/v1/users/me/"):
        return path
    if path.startswith("/v1/workspaces/"):
        return path
    if path.startswith("/v1/"):
        return f"/v1/workspaces/{workspace_slug}{path[3:]}"
    raise ValueError("Plane API paths must start with /v1/.")


def _validate_generic_path(path: str) -> str:
    candidate = path if path.startswith("/") else f"/{path}"
    if not candidate.startswith("/v1/"):
        raise ValueError("Generic Plane API requests must start with /v1/.")
    return candidate


def _csv(values: list[str] | None) -> str | None:
    if not values:
        return None
    return ",".join(values)


def _rewrite_host_header(headers: list[tuple[bytes, bytes]], host_value: bytes) -> list[tuple[bytes, bytes]]:
    filtered = [(key, value) for key, value in headers if key.lower() != b"host"]
    filtered.append((b"host", host_value))
    return filtered
