from __future__ import annotations

from typing import Any

import httpx

from .auth import PlaneAuthContext
from .config import ServerSettings


class PlaneAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, detail: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class PlaneAPIClient:
    def __init__(self, settings: ServerSettings, auth: PlaneAuthContext):
        self.settings = settings
        self.auth = auth

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        allow_mutation: bool = False,
    ) -> Any:
        normalized_method = method.upper()
        if allow_mutation and not self.settings.allow_mutations:
            raise PlaneAPIError("Mutating Plane actions are disabled on this server.")

        path = path if path.startswith("/") else f"/{path}"
        if not path.startswith("/v1/"):
            raise PlaneAPIError("Plane API paths must start with /v1/.")

        url = f"{self.auth.base_url}{path}"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": "plane-mcp-server/0.1.0",
            "x-api-key": self.auth.api_key,
        }

        timeout = httpx.Timeout(self.settings.request_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.request(
                normalized_method,
                url,
                headers=headers,
                params=_strip_none(params),
                json=_strip_none(json_body),
            )

        if response.status_code >= 400:
            detail = _decode_response(response)
            raise PlaneAPIError(
                f"Plane API request failed with status {response.status_code}.",
                status_code=response.status_code,
                detail=detail,
            )

        return _decode_response(response)


def _decode_response(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.json()
    return response.text


def _strip_none(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {key: item for key, item in value.items() if item is not None}
