# Client Matrix

This matrix documents the discovery targets supported by version 0.1.

| Client | Project Config | User Config | Format | Server Key | Notes |
| --- | --- | --- | --- | --- | --- |
| Claude Code | `.mcp.json` | `~/.claude.json` | JSON | `mcpServers` | User config discovery supports top-level servers and project-scoped servers when the project path matches. |
| Codex | `.codex/config.toml` | `~/.codex/config.toml` | TOML | `mcp_servers` | Supports stdio server entries from Codex config tables. |
| Cursor | `.cursor/mcp.json` | `~/.cursor/mcp.json` | JSON | `mcpServers` | Supports stdio, HTTP, and SSE shapes. |
| VS Code | `.vscode/mcp.json` | Not yet | JSON | `servers` | Workspace config is supported in version 0.1. |
| Windsurf | Not yet | `~/.codeium/windsurf/mcp_config.json`, `~/.codeium/mcp_config.json` | JSON | `mcpServers` | Global config paths are supported. |

## Normalized Fields

Every discovered server is normalized to:

- `id`
- `client`
- `scope`
- `path`
- `transport`
- `command`
- `args`
- `env`
- `url`
- `headers`
- `cwd`
- `enabled`

Unknown client-specific fields are preserved in the raw model for future checks, but reports focus on portable fields.
