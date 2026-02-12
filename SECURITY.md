# Security Policy

## Supported Versions

Only the latest release is supported with security updates.

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |
| Older   | No        |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, use [GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) feature on this repository.

Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You should receive an initial response within 48 hours. We will keep you informed of progress towards a fix and release.

## Security Considerations

This project handles AWX credentials via environment variables. Please ensure:

- Credentials are never baked into Docker images
- Environment files (`.env`) are excluded from version control
- The MCP server is only accessible locally via stdio transport
- All AWX API access is read-only by design
