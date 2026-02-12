# Contributing to AWX MCP Server

Thanks for your interest in contributing! This document outlines how to get involved.

Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold it.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a feature branch from `main`
4. Make your changes
5. Test your changes (see [Testing](#testing))
6. Submit a pull request

## Development Setup

### Prerequisites

- Docker installed and running
- Python 3.13+ (for local development without Docker)
- AWX instance with API access (for integration testing)

### Building

```bash
docker build -t awx-mcp-server:dev .
```

### Testing

Test the MCP server responds to protocol requests:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"0.1.0"}}}' \
  | docker run -i --rm \
    -e AWX_URL=https://awx.example.com \
    -e AWX_USERNAME=test \
    -e AWX_PASSWORD=test \
    awx-mcp-server:dev
```

### Adding a New Tool

1. Add the AWX API method to `src/awx_client.py`
2. Register the tool with `@mcp.tool()` in `src/awx_mcp_server.py`
3. Rebuild the Docker image
4. Update `readme.md` with the new tool's documentation

## Guidelines

- **Read-only**: All tools must use GET requests only. This is a deliberate security constraint.
- **British English**: Use British English in code, comments, and documentation.
- **Minimal dependencies**: Avoid adding new dependencies unless absolutely necessary.
- **Error handling**: Tools should catch exceptions and return user-friendly error strings, never raise to the MCP layer.

## Pull Requests

- Keep PRs focused on a single change
- Include a clear description of what and why
- Update documentation if adding or changing tools
- Ensure the Docker image builds cleanly

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Include the MCP server version and how you're running it (Docker tag, local, etc.)
- For bugs, include the JSON-RPC request/response if possible

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
