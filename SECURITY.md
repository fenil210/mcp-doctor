# Security Policy

Agent Plugin Diagnostics is local-first. It does not collect telemetry and does not send configuration data to a remote service.

## Supported Versions

The project is pre-1.0. Security fixes will target the latest published version and the `main` branch.

## Reporting a Vulnerability

If GitHub security advisories are enabled for this repository, please report vulnerabilities through a private advisory. If advisories are not available, open an issue with a minimal description and avoid posting secrets, tokens, exploit payloads, or private config values.

Useful reports include:

- Affected command or package version.
- A minimal config that reproduces the behavior.
- Expected behavior.
- Actual behavior.
- Whether the issue can expose local files, environment variables, credentials, or network access.

## Probe Safety

`apd probe` starts configured stdio MCP servers only for a controlled initialize and tools/list sequence. It uses explicit argument arrays, timeouts, and process cleanup. It does not call arbitrary tools.

Remote HTTP and SSE probing is intentionally not implemented in the first release.

## Secret Handling

Reports redact values that look like tokens, API keys, passwords, bearer credentials, or common provider secrets. Redaction is best effort. Do not paste private production configuration into public issues.
