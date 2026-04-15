# plane-mcp-server

An MCP server for [Plane](https://plane.so). Connect your AI assistant to your Plane workspace and let it read and manage projects, work items, cycles, and more.

Runs as a hosted HTTP service for your whole team, or locally over `stdio` for a single user.

## What you can do

Once connected, your assistant can:

- Browse projects, states, cycles, modules, labels, and work item types
- Search and read work items, comments, and relations
- Create or update work items (optional, off by default)
- Add comments and work logs (optional, off by default)
- Call any newer Plane API endpoint via a fallback tool, for things not yet wrapped as first-class tools

## Quick start

Pick the path that fits you.

### Option A — You're a user connecting to an existing server

Ask your admin for the server URL, then add it to your MCP client. Most clients accept a JSON config in this shape:

```json
{
  "mcpServers": {
    "plane": {
      "url": "https://plane-mcp.example.com/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_PLANE_API_KEY>",
        "X-Workspace-Slug": "your-workspace-slug"
      }
    }
  }
}
```

Get your Plane API key at **Settings → API Tokens** in Plane.

That's it — no installs, no local Python, no `uvx`/`npx`.

### Option B — You want to run it yourself over `stdio` (solo use)

```bash
pip install .

PLANE_API_KEY="plane_api_key" \
PLANE_WORKSPACE_SLUG="your-workspace-slug" \
PLANE_BASE_URL="https://plane.example.com/api" \
plane-mcp-server stdio
```

Then point your MCP client at the `plane-mcp-server stdio` command.

### Option C — You're hosting the server for a team

```bash
pip install .

PLANE_DEFAULT_BASE_URL="https://plane.example.com/api" \
PLANE_ALLOWED_BASE_URLS="https://plane.example.com/api" \
PLANE_ALLOW_MUTATIONS="true" \
plane-mcp-server streamable-http
```

Or with Docker:

```bash
docker build -t plane-mcp-server .
docker run -p 8000:8000 \
  -e PLANE_DEFAULT_BASE_URL="https://plane.example.com/api" \
  -e PLANE_ALLOWED_BASE_URLS="https://plane.example.com/api" \
  -e PLANE_ALLOW_MUTATIONS="true" \
  plane-mcp-server
```

Your users then connect with their own Plane API key — see Option A.

## How auth works

Each request carries the user's own Plane API key, so the server never stores tokens and every action is scoped to whoever made the call.

| Header | Required | Purpose |
| --- | --- | --- |
| `Authorization: Bearer <PLANE_API_KEY>` | yes | The user's personal Plane API token |
| `X-Workspace-Slug: <slug>` | yes | Which Plane workspace to target |
| `X-Plane-Base-Url: <url>` | no | Override the Plane host (must be in the server's allowlist) |

## Configuration

All configuration is via environment variables.

### Common

| Variable | Default | Description |
| --- | --- | --- |
| `PLANE_DEFAULT_BASE_URL` | `https://api.plane.so/api` | Default Plane API base URL |
| `PLANE_ALLOWED_BASE_URLS` | the default above | Comma-separated allowlist of Plane hosts clients may target |
| `PLANE_ALLOW_MUTATIONS` | `false` | Set to `true` to enable create/update/comment/worklog tools |
| `PLANE_REQUEST_TIMEOUT_SECONDS` | `30` | Upstream request timeout |

### HTTP transport

| Variable | Default | Description |
| --- | --- | --- |
| `PLANE_MCP_HOST` | `0.0.0.0` | Bind host |
| `PLANE_MCP_PORT` | `8000` | Bind port |
| `PLANE_MCP_PUBLIC_BASE_URL` | — | Public URL when running behind a reverse proxy (e.g. `https://plane-mcp.example.com`) |
| `PLANE_MCP_TRUSTED_HOST` | `127.0.0.1:8000` | Internal host header to present behind a proxy |
| `PLANE_CORS_ORIGINS` | — | Comma-separated CORS origins, only needed for browser-based clients |
| `PLANE_ALLOW_HTTP_BASE_URLS` | `false` | Allow `http://` base URLs (local dev only) |

### stdio transport

| Variable | Required | Description |
| --- | --- | --- |
| `PLANE_API_KEY` | yes | Your Plane API token |
| `PLANE_WORKSPACE_SLUG` | yes | Your Plane workspace slug |
| `PLANE_BASE_URL` | no | Plane host override (defaults to `PLANE_DEFAULT_BASE_URL`) |

## Deploying behind a reverse proxy

Use a dedicated subdomain like `plane-mcp.example.com` pointing at the container.

- Container port: `8000`
- Health check endpoint: `GET /healthz`
- MCP endpoint: `https://plane-mcp.example.com/mcp`

Set `PLANE_MCP_PUBLIC_BASE_URL` to the public URL your clients will use, and `PLANE_MCP_TRUSTED_HOST` to the internal `host:port` the proxy forwards to (e.g. `127.0.0.1:8000`).

## Security model

- Tokens are never stored — each request carries its own
- Auth is scoped per-request via `contextvars`, so requests never bleed into each other
- Upstream Plane hosts are normalized and allowlisted to prevent SSRF
- Mutating tools are disabled by default (`PLANE_ALLOW_MUTATIONS=false`)
- Requests use a fixed timeout and do not follow redirects
- Logs do not include request headers

## Troubleshooting

**`401 authentication_required`** — Check that both `Authorization: Bearer …` and `X-Workspace-Slug` headers are set.

**`Base URL is not allowed`** — The `X-Plane-Base-Url` your client sent isn't in `PLANE_ALLOWED_BASE_URLS`. Either remove the header (to use the server default) or ask the admin to add it.

**`Mutating Plane actions are disabled on this server.`** — The server was started without `PLANE_ALLOW_MUTATIONS=true`. Read-only tools still work.

**Tool not found for a new Plane endpoint** — Use the `plane_api_request` fallback tool; it can call any current `/v1/...` path.

## Development

```bash
pip install -e .
plane-mcp-server stdio
```

Transports:
- `stdio` — for local single-user development
- `streamable-http` — recommended for production
- `sse` — legacy, deprecated by MCP

## References

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Plane developer docs](https://developers.plane.so/dev-tools/mcp-server)
