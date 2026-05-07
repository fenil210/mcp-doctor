# Client Matrix

This matrix documents the discovery targets supported by version 0.1.

| Client | Project Config | User Config | Format | Server Key | Notes |
| --- | --- | --- | --- | --- | --- |
| Claude Desktop | Not applicable | `~/Library/Application Support/Claude/claude_desktop_config.json`, `~/AppData/Roaming/Claude/claude_desktop_config.json` | JSON | `mcpServers` | The two paths are the official macOS and Windows desktop app config locations. |
| Claude Code | `.mcp.json` | `~/.claude.json` | JSON | `mcpServers` | User config discovery supports top-level servers and project-scoped servers when the project path matches. |
| Cline | Not yet | `~/.cline/data/settings/cline_mcp_settings.json` | JSON | `mcpServers` | Covers the documented Cline CLI MCP settings file. |
| Codex | `.codex/config.toml` | `~/.codex/config.toml` | TOML | `mcp_servers` | Supports stdio server entries from Codex config tables. |
| Cursor | `.cursor/mcp.json` | `~/.cursor/mcp.json` | JSON | `mcpServers` | Supports stdio, HTTP, and SSE shapes. |
| OpenCode | `opencode.json` | `~/.config/opencode/opencode.json` | JSON | `mcp` | Supports current OpenCode local and remote MCP entries. |
| Roo Code | `.roo/mcp.json` | Not yet | JSON | `mcpServers` | Covers Roo Code project-level MCP configuration. |
| VS Code | `.vscode/mcp.json` | Not yet | JSON | `servers` | Workspace config is supported in version 0.1. |
| Windsurf | Not yet | `~/.codeium/windsurf/mcp_config.json`, `~/.codeium/mcp_config.json` | JSON | `mcpServers` | Global config paths are supported. |
| Zed | `.zed/settings.json` | `~/.config/zed/settings.json`, `~/.zed/settings.json`, `~/AppData/Roaming/Zed/settings.json` | JSON | `context_servers` | Supports Zed context server settings. |

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
