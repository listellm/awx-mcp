# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWX MCP Server - A Model Context Protocol server providing AWX API integration tools for Claude Code. This is a **local developer tool** that runs in Docker via stdio transport, not a Kubernetes workload.

## Architecture

- **Transport**: stdio (stdin/stdout JSON-RPC)
- **Framework**: FastMCP (official MCP Python SDK)
- **Deployment**: Docker container, pulled from Harbor by developers
- **Authentication**: HTTP Basic Auth via environment variables

## Development Commands

### Build Image
```bash
docker build -t awx-mcp-server:dev .
```

### Test Locally (Manual stdio)
```bash
# Simple ping test
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  | docker run -i --rm \
    -e AWX_URL=https://awx.example.com \
    -e AWX_USERNAME=test \
    -e AWX_PASSWORD=test \
    awx-mcp-server:dev
```

### Interactive Testing
```bash
# Start container in interactive mode
docker run -i --rm --env-file .env awx-mcp-server:dev

# Then send JSON-RPC requests line by line:
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "awx_list_recent_jobs", "arguments": {"limit": 5}}}
```

### Verify in Claude Code
After configuring `.vscode/mcp.json`, use:
```
ToolSearch(query="awx")
```
Should return 7 tools prefixed with `mcp__awx__`

## Code Structure

```
src/
├── awx_mcp_server.py   # FastMCP server + tool definitions
├── awx_client.py       # AWX API wrapper (requests-based)
└── __init__.py

Dockerfile              # Multi-stage build (Python 3.13 slim)
requirements.txt        # mcp + requests only
```

### Key Design Patterns

#### Tool Definition Pattern
Each MCP tool in `awx_mcp_server.py` follows this structure:
```python
@mcp.tool()
def awx_tool_name(param: Type) -> str:
    """Docstring becomes tool description in MCP."""
    try:
        result = awx_client.method(param)
        return formatted_output
    except AWXClientError as e:
        return f"AWX Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"
```

**Important**: All tools return `str` (formatted markdown), not raw JSON. This is by design for Claude Code consumption.

#### Error Handling Strategy
- `AWXClient._request()` translates HTTP errors to `AWXClientError`
- Tool functions catch `AWXClientError` and return user-friendly messages
- Generic `Exception` catch for unexpected failures
- **Never raise exceptions to MCP layer** - always return error strings

#### Pagination Pattern
Two approaches used:
1. **Exposed to user**: `awx_list_inventories(page, page_size)` - lets caller control pagination
2. **Internal exhaustion**: `get_inventory_hosts()` - auto-paginates until `next` is None

#### Polling Pattern
`awx_stream_job_logs(follow=True)` implements polling:
- Check job status every 2 seconds
- Track `start_line` to avoid re-fetching old logs
- Break when status is terminal (successful/failed/canceled/error)

## Adding New Tools

1. Add API method to `AWXClient` in `awx_client.py`
   - Use `_request()` for HTTP calls
   - Raise `AWXClientError` on failures
   - Return Dict/List/str, not Response objects

2. Define tool in `awx_mcp_server.py`
   - Use `@mcp.tool()` decorator
   - Type hints become parameter schemas
   - Docstring becomes tool description
   - Return formatted string (markdown), not JSON

3. Rebuild Docker image

4. Update README.md tool list

## Configuration Requirements

Required environment variables:
- `AWX_URL` - AWX base URL (trailing slash removed automatically)
- `AWX_USERNAME` - AWX username
- `AWX_PASSWORD` - AWX password

These MUST be provided via Docker `-e` flags or `--env-file`. Never baked into image.

## Constraints & Design Decisions

- **Read-only**: All tools use GET requests only (no POST/PUT/DELETE/PATCH)
- **No job launching**: Cannot trigger AWX jobs (intentional security constraint)
- **No WebSocket**: AWX API doesn't support WS, so log streaming uses polling
- **No caching**: Always fetches live data from AWX API
- **Stateless**: Each request is independent, no persistent state
- **Single instance**: One container = one AWX connection

## Security Notes

- No exposed ports (stdio-only, no EXPOSE in Dockerfile)
- Credentials passed via environment (not args or config files)
- All API calls authenticated via HTTP Basic Auth
- Minimal dependencies (only mcp + requests)
- Multi-stage build to exclude build tools from runtime image

## CI/CD

Configure your CI/CD pipeline to:
- Build the Docker image on code changes
- Push to your container registry
- Tag with your preferred versioning scheme (e.g., semantic versioning, build numbers)

## Common Issues

### Tools not appearing in Claude Code
- Verify `.vscode/mcp.json` exists and is valid JSON
- Check Docker image is built: `docker images awx-mcp-server`
- Restart Claude Code completely (not just reload)

### Authentication failures
- Verify environment variables are set before launching Claude Code
- Test credentials: `curl -u "user:pass" https://awx.example.com/api/v2/ping/`

### Container cannot reach AWX
- Check VPN connection (AWX requires internal network)
- Consider adding `--network host` to Docker args if container networking is isolated
