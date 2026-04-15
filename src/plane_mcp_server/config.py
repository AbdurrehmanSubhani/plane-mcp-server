from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_plane_base_url(base_url: str, *, allow_http: bool = False) -> str:
    candidate = base_url.strip().rstrip("/")
    parsed = urlparse(candidate)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError("Plane base URL must include http or https.")
    if parsed.scheme != "https" and not allow_http:
        raise ValueError("Plain HTTP base URLs are disabled.")
    if not parsed.netloc:
        raise ValueError("Plane base URL must include a hostname.")
    path = parsed.path.rstrip("/")
    if not path:
        path = "/api"
    normalized = parsed._replace(path=path, params="", query="", fragment="")
    return normalized.geturl().rstrip("/")


@dataclass(frozen=True)
class ServerSettings:
    host: str
    port: int
    default_base_url: str
    allowed_base_urls: tuple[str, ...]
    allow_http_base_urls: bool
    allow_mutations: bool
    request_timeout_seconds: float
    cors_origins: tuple[str, ...]
    public_base_url: str | None
    server_name: str = "Plane MCP Server"

    @classmethod
    def from_env(cls) -> "ServerSettings":
        allow_http = _parse_bool(os.getenv("PLANE_ALLOW_HTTP_BASE_URLS"), default=False)
        default_base_url = normalize_plane_base_url(
            os.getenv("PLANE_DEFAULT_BASE_URL", "https://api.plane.so/api"),
            allow_http=allow_http,
        )
        allowed = _parse_csv(os.getenv("PLANE_ALLOWED_BASE_URLS"))
        allowed_base_urls = tuple(
            normalize_plane_base_url(item, allow_http=allow_http) for item in allowed
        ) or (default_base_url,)
        return cls(
            host=os.getenv("PLANE_MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("PLANE_MCP_PORT", "8000")),
            default_base_url=default_base_url,
            allowed_base_urls=allowed_base_urls,
            allow_http_base_urls=allow_http,
            allow_mutations=_parse_bool(os.getenv("PLANE_ALLOW_MUTATIONS"), default=False),
            request_timeout_seconds=float(os.getenv("PLANE_REQUEST_TIMEOUT_SECONDS", "30")),
            cors_origins=tuple(_parse_csv(os.getenv("PLANE_CORS_ORIGINS"))),
            public_base_url=(os.getenv("PLANE_MCP_PUBLIC_BASE_URL") or "").strip() or None,
        )

    def is_allowed_base_url(self, base_url: str) -> bool:
        return base_url in self.allowed_base_urls
