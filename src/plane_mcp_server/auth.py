from __future__ import annotations

import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Mapping

from .config import ServerSettings, normalize_plane_base_url


@dataclass(frozen=True)
class PlaneAuthContext:
    api_key: str
    workspace_slug: str
    base_url: str
    source: str


class PlaneAuthError(RuntimeError):
    pass


_current_auth: ContextVar[PlaneAuthContext | None] = ContextVar("plane_auth", default=None)


def _extract_bearer_token(headers: Mapping[str, str]) -> str | None:
    authorization = headers.get("authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        return token or None
    for key in ("x-api-key", "x-plane-api-key", "plane-api-key"):
        token = headers.get(key, "").strip()
        if token:
            return token
    return None


def _extract_workspace_slug(headers: Mapping[str, str]) -> str | None:
    for key in ("x-workspace-slug", "plane-workspace-slug"):
        value = headers.get(key, "").strip()
        if value:
            return value
    return None


def _extract_base_url(headers: Mapping[str, str], settings: ServerSettings) -> str:
    for key in (
        "x-plane-base-url",
        "x-plane-api-host-url",
        "plane-base-url",
        "plane-api-host-url",
    ):
        value = headers.get(key, "").strip()
        if value:
            base_url = normalize_plane_base_url(value, allow_http=settings.allow_http_base_urls)
            if not settings.is_allowed_base_url(base_url):
                raise PlaneAuthError(f"Base URL is not allowed: {base_url}")
            return base_url
    return settings.default_base_url


def resolve_http_auth(headers: Mapping[str, str], settings: ServerSettings) -> PlaneAuthContext:
    api_key = _extract_bearer_token(headers)
    workspace_slug = _extract_workspace_slug(headers)
    if not api_key:
        raise PlaneAuthError("Missing Plane API key. Use Authorization: Bearer <token>.")
    if not workspace_slug:
        raise PlaneAuthError("Missing X-Workspace-Slug header.")
    base_url = _extract_base_url(headers, settings)
    return PlaneAuthContext(
        api_key=api_key,
        workspace_slug=workspace_slug,
        base_url=base_url,
        source="http-headers",
    )


def resolve_stdio_auth(settings: ServerSettings) -> PlaneAuthContext:
    api_key = (os.getenv("PLANE_API_KEY") or os.getenv("PLANE_ACCESS_TOKEN") or "").strip()
    workspace_slug = (os.getenv("PLANE_WORKSPACE_SLUG") or "").strip()
    base_url = normalize_plane_base_url(
        os.getenv("PLANE_BASE_URL", settings.default_base_url),
        allow_http=settings.allow_http_base_urls,
    )
    if not settings.is_allowed_base_url(base_url):
        raise PlaneAuthError(f"Base URL is not allowed: {base_url}")
    if not api_key or not workspace_slug:
        raise PlaneAuthError(
            "PLANE_API_KEY or PLANE_ACCESS_TOKEN and PLANE_WORKSPACE_SLUG are required for stdio."
        )
    return PlaneAuthContext(
        api_key=api_key,
        workspace_slug=workspace_slug,
        base_url=base_url,
        source="environment",
    )


def get_auth_context(settings: ServerSettings) -> PlaneAuthContext:
    current = _current_auth.get()
    if current is not None:
        return current
    return resolve_stdio_auth(settings)


def set_current_auth(auth: PlaneAuthContext | None):
    return _current_auth.set(auth)


def reset_current_auth(token) -> None:
    _current_auth.reset(token)
