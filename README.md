# AWX MCP Server

Model Context Protocol (MCP) server that provides structured tools for interacting with the AWX API. This enables Claude Code to query job status, stream logs, inspect inventories, and search templates without constructing manual curl commands.

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│ Claude Code (Main Agent)                                     │
│   │                                                          │
│   ├──calls──> mcp__awx__get_job_status                      │
│   ├──calls──> mcp__awx__stream_job_logs                     │
│   ├──calls──> mcp__awx__list_inventories                    │
│   └──calls──> mcp__awx__search_job_templates                │
│                                                              │
│   via stdio (stdin/stdout)                                   │
└───────────────────┬──────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ AWX MCP Server (Docker Container)                           │
│   - Reads JSON-RPC requests from stdin                      │
│   - Writes JSON-RPC responses to stdout                     │
│   - Wraps AWX API with authentication                       │
└───────────────────┬──────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ AWX API (/api/v2/)                                          │
└─────────────────────────────────────────────────────────────┘
```

This is a **local developer tool** that runs in Docker via stdio transport.

## Features

- **Job Status Queries**: Check status, runtime, and details of AWX jobs
- **Log Streaming**: View job execution output (with optional real-time polling)
- **Inventory Management**: List inventories, view hosts, inspect host variables
- **Template Search**: Find available job templates and playbooks
- **Job History**: View recent job executions with filtering

## Quick Start

### Prerequisites

- Docker installed and running
- AWX credentials (URL, username, password)

### Using Published Image

Pull the latest release from GitHub Container Registry:

```bash
docker pull ghcr.io/listellm/awx-mcp:latest
```

Or use a specific version:

```bash
docker pull ghcr.io/listellm/awx-mcp:v1.0.1
```

### Build from Source

Alternatively, build locally:

```bash
docker build -t awx-mcp-server:latest .
```

### Configure Claude Code

Add to `.vscode/mcp.json` in your project:

```json
{
  "servers": {
    "awx": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "AWX_URL",
        "-e", "AWX_USERNAME",
        "-e", "AWX_PASSWORD",
        "ghcr.io/listellm/awx-mcp:latest"
      ]
    }
  }
}
```

> **Note**: Replace `ghcr.io/listellm/awx-mcp:latest` with `awx-mcp-server:latest` if you built from source.

Set the environment variables in your shell before launching Claude Code, or use `--env-file`:

```json
{
  "servers": {
    "awx": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--env-file", "/path/to/.env",
        "ghcr.io/listellm/awx-mcp:latest"
      ]
    }
  }
}
```

### Verify

After restarting Claude Code, use `ToolSearch(query="awx")` to confirm all 7 tools are available.

## Available Tools

All tools are **read-only** (GET requests only). Prefixed with `mcp__awx__` in Claude Code.

### `awx_get_job_status`

Get status and details of an AWX job.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | integer | yes | AWX job ID |

### `awx_stream_job_logs`

Retrieve job execution logs, with optional polling for running jobs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | integer | yes | AWX job ID |
| `follow` | boolean | no | Poll until job completes (default: false) |

### `awx_list_inventories`

List available AWX inventories.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | no | Page number (default: 1) |
| `page_size` | integer | no | Results per page (default: 50) |

### `awx_get_inventory_hosts`

Get all hosts in an inventory. Provide either `inventory_id` or `inventory_name`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `inventory_id` | integer | one of | Inventory ID |
| `inventory_name` | string | one of | Inventory name |

### `awx_get_host_variables`

Get variables for a specific host. Provide either `host_id` or `host_name`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `host_id` | integer | one of | Host ID |
| `host_name` | string | one of | Host FQDN |

### `awx_search_job_templates`

Search for AWX job templates.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name_filter` | string | no | Substring match on template name |
| `limit` | integer | no | Maximum results (default: 50) |

### `awx_list_recent_jobs`

List recent AWX job executions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | no | Filter: successful, failed, running, pending, canceled, error |
| `limit` | integer | no | Maximum results (default: 20) |

## Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `AWX_URL` | AWX base URL (e.g., `https://awx.example.com`) | yes |
| `AWX_USERNAME` | AWX username | yes |
| `AWX_PASSWORD` | AWX password | yes |

## Testing

### Manual stdio test

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  | docker run -i --rm \
    -e AWX_URL=https://awx.example.com \
    -e AWX_USERNAME=test \
    -e AWX_PASSWORD=test \
    ghcr.io/listellm/awx-mcp:latest
```

Expected response:

```json
{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "0.1.0", "serverInfo": {"name": "awx-mcp-server", "version": "0.1.0"}, "capabilities": {"tools": {}}}}
```

### Interactive testing

```bash
docker run -i --rm --env-file .env ghcr.io/listellm/awx-mcp:latest
```

Then send JSON-RPC requests line by line:

```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "awx_list_recent_jobs", "arguments": {"limit": 5}}}
```

Press `Ctrl+D` to exit.

## Troubleshooting

### Tools not found in Claude Code

- Verify `.vscode/mcp.json` exists and is valid JSON
- Check the image is built: `docker images awx-mcp-server`
- Restart Claude Code completely (not just reload)
- Use `ToolSearch(query="awx")` to verify

### Authentication failed

- Verify environment variables contain correct credentials
- Test manually: `curl -u "user:pass" https://awx.example.com/api/v2/ping/`

### Cannot connect to AWX

- Check network connectivity to AWX instance
- Verify the Docker container can reach AWX (host networking may be needed with `--network host`)

## Security

- **Read-only**: All tools perform GET requests only
- **No ports**: stdio-only (no EXPOSE, no listening sockets)
- **Credentials via env**: Not baked into image
- **Stateless**: No persistent storage

## Limitations

- **No job launching**: Cannot trigger AWX jobs (by design)
- **Polling-based streaming**: Log streaming polls every 2 seconds (AWX has no WebSocket support)
- **Single instance**: Configured for one AWX instance per container
- **No caching**: Always fetches live data from AWX API

## Development

### Adding new tools

1. Add AWX API method to `src/awx_client.py`
2. Register tool with `@mcp.tool()` decorator in `src/awx_mcp_server.py`
3. Implement tool handler function
4. Rebuild Docker image

### Dependencies

- **mcp**: Official Model Context Protocol Python SDK
- **requests**: HTTP client for AWX API calls
- Standard library only otherwise (minimises attack surface)

## Related

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [AWX Project](https://github.com/ansible/awx)
- [Claude Code](https://claude.ai/code)

## Installation

### Docker Image

Published releases are available on GitHub Container Registry:

```bash
docker pull ghcr.io/listellm/awx-mcp:latest    # Latest stable
docker pull ghcr.io/listellm/awx-mcp:v1        # Latest v1.x
docker pull ghcr.io/listellm/awx-mcp:v1.0      # Latest v1.0.x
docker pull ghcr.io/listellm/awx-mcp:v1.0.1    # Specific version
```

Images are automatically built and published on every release via GitHub Actions.

## Releases

See [GitHub Releases](https://github.com/listellm/awx-mcp/releases) for the full changelog and release notes.

- **v1.0.x**: Production-ready with automated releases
- **v0.1.0**: Initial implementation
