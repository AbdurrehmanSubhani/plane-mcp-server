# plane-mcp-server

Remote-first MCP server for Plane that works with `streamable-http` and `stdio`.

## Goals

- remove `uvx` / `npx` / Node / Python requirements from employee laptops
- let each user connect with their own Plane API key
- keep the server safe to publish later as a general-purpose open source MCP
- stay aligned with current MCP production guidance: stateless streamable HTTP with JSON responses

## Features

- `streamable-http` transport on `/mcp`
- optional `stdio` transport for local debugging
- per-request auth via:
  - `Authorization: Bearer <PLANE_API_KEY>`
  - `X-Workspace-Slug: <workspace-slug>`
  - `X-Plane-Base-Url: https://plane.example.com/api` optional
- SSRF protection through a base-URL allowlist
- mutation guard via `PLANE_ALLOW_MUTATIONS`
- current typed tools for projects, work items, states, cycles, modules, labels, comments, and work logs
- guarded `plane_api_request` fallback for newer Plane endpoints

## Security Model

- the server never stores user Plane tokens
- request auth is scoped to the current MCP request via `contextvars`
- upstream Plane base URLs are normalized and checked against `PLANE_ALLOWED_BASE_URLS`
- mutating tools can be disabled globally with `PLANE_ALLOW_MUTATIONS=false`
- requests use a fixed timeout and do not follow arbitrary redirects
- logs should not include request headers

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `PLANE_DEFAULT_BASE_URL` | no | Default Plane API base URL. Defaults to `https://api.plane.so/api`. |
| `PLANE_ALLOWED_BASE_URLS` | no | Comma-separated allowlist for upstream Plane API base URLs. Defaults to `PLANE_DEFAULT_BASE_URL`. |
| `PLANE_ALLOW_HTTP_BASE_URLS` | no | Set to `true` only for local development over plain HTTP. |
| `PLANE_ALLOW_MUTATIONS` | no | Set to `true` to enable create, update, comment, and worklog tools. Defaults to `false`. |
| `PLANE_REQUEST_TIMEOUT_SECONDS` | no | Upstream request timeout. Defaults to `30`. |
| `PLANE_MCP_HOST` | no | HTTP bind host. Defaults to `0.0.0.0`. |
| `PLANE_MCP_PORT` | no | HTTP bind port. Defaults to `8000`. |
| `PLANE_CORS_ORIGINS` | no | Comma-separated CORS origins for browser-based MCP clients. Keep empty unless needed. |
| `PLANE_API_KEY` | no | Fallback token for `stdio` mode only. |
| `PLANE_WORKSPACE_SLUG` | no | Fallback workspace slug for `stdio` mode only. |
| `PLANE_BASE_URL` | no | Fallback Plane base URL for `stdio` mode only. |

## Run

Install:

```bash
pip install .
```

Run over streamable HTTP:

```bash
PLANE_DEFAULT_BASE_URL="https://plane.example.com/api" \
PLANE_ALLOWED_BASE_URLS="https://plane.example.com/api" \
PLANE_ALLOW_MUTATIONS="true" \
plane-mcp-server streamable-http
```

Run locally over stdio:

```bash
PLANE_API_KEY="plane_api_key" \
PLANE_WORKSPACE_SLUG="workspace-slug" \
PLANE_BASE_URL="https://plane.example.com/api" \
plane-mcp-server stdio
```

## LobeChat Import JSON

```json
{
  "mcpServers": {
    "plane": {
      "url": "https://plane-mcp.coldpeak.co/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_PLANE_API_KEY>",
        "X-Workspace-Slug": "grayhat",
        "X-Plane-Base-Url": "https://plane.coldpeak.co/api"
      }
    }
  }
}
```

If the server already pins `PLANE_DEFAULT_BASE_URL`, clients can omit `X-Plane-Base-Url`.

## Coolify

Use a dedicated host such as `plane-mcp.coldpeak.co`.

- build context: repo root
- Dockerfile: included
- container port: `8000`
- health check: `GET /healthz`
- route MCP clients to `https://plane-mcp.coldpeak.co/mcp`

## MCP References

- MCP production guidance recommends `streamable-http` for production deployments and `stateless_http=True` with JSON responses for scalability.
- Browser-based MCP clients need `Mcp-Session-Id` exposed through CORS when CORS is enabled.

Sources:

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Plane developer docs](https://developers.plane.so/dev-tools/mcp-server)
