from __future__ import annotations

import argparse

import uvicorn

from .config import ServerSettings
from .server import create_http_app, create_mcp


def main() -> int:
    parser = argparse.ArgumentParser(description="Plane MCP Server")
    parser.add_argument(
        "transport",
        choices=["stdio", "streamable-http", "sse"],
        help="Transport to run.",
    )
    args = parser.parse_args()
    settings = ServerSettings.from_env()

    if args.transport == "stdio":
        create_mcp(settings).run()
        return 0

    if args.transport == "sse":
        create_mcp(settings).run(transport="sse")
        return 0

    uvicorn.run(
        create_http_app(settings),
        host=settings.host,
        port=settings.port,
        proxy_headers=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
