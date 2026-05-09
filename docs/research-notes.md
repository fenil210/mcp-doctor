# Research Notes

This document records the public documentation used for the current discovery and probing behavior. It is intentionally limited to source-backed behavior.

## Client Configuration Sources

- Claude Desktop uses `claude_desktop_config.json` for desktop MCP server configuration. The MCP quickstart documents the macOS path `~/Library/Application Support/Claude/claude_desktop_config.json` and the Windows path `%APPDATA%\Claude\claude_desktop_config.json`: https://modelcontextprotocol.io/docs/develop/connect-local-servers
- Cline documents CLI MCP settings at `~/.cline/data/settings/cline_mcp_settings.json`: https://docs.cline.bot/cline-cli/configuration
- Codex MCP configuration uses `mcp_servers` entries in Codex config: https://developers.openai.com/codex/config-reference
- Cursor documents project `.cursor/mcp.json` and global `~/.cursor/mcp.json` MCP configuration: https://docs.cursor.com/context/mcp
- OpenCode documents global `~/.config/opencode/opencode.json`, project `opencode.json`, and MCP config under the `mcp` key: https://opencode.ai/docs/config
- Roo Code documents project-level `.roo/mcp.json` with `mcpServers`: https://docs.roocode.com/features/mcp/using-mcp-in-roo
- VS Code documents workspace `.vscode/mcp.json` with a `servers` map: https://code.visualstudio.com/docs/copilot/reference/mcp-configuration
- Windsurf documents `~/.codeium/windsurf/mcp_config.json` MCP configuration: https://docs.windsurf.com/windsurf/cascade/mcp
- Zed documents MCP context servers through `context_servers` in settings and project/user settings files: https://zed.dev/docs/ai/mcp and https://zed.dev/docs/configuring-zed

## Real App Integration Sources

The real app integration harness only uses source-backed commands and config paths:

- Claude Code documents the `claude` CLI and `claude mcp` command group: https://code.claude.com/docs/en/cli-reference
- Claude support documents the native installer placing `claude` under `~/.local/bin` and `%USERPROFILE%\.local\bin`: https://support.claude.com/en/articles/14554922-claude-code-user-faq
- Cline CLI documents `cline config`, `cline mcp`, and the MCP config path used by the CLI: https://docs.cline.bot/cline-cli/configuration
- Cursor documents Cursor CLI and that the CLI respects `mcp.json`: https://docs.cursor.com/en/cli/using
- Cursor CLI reference documents `cursor-agent mcp`: https://docs.cursor.com/en/cli/reference/parameters
- Windsurf documents that the `windsurf` command can be installed in `PATH`: https://docs.windsurf.com/windsurf
- Zed documents the `zed` CLI: https://zed.dev/docs/reference/cli.html

## Protocol Sources

The MCP specification and documentation define the protocol behavior that APD validates:

- The current protocol version is `2025-06-18`: https://modelcontextprotocol.io/specification/
- All MCP messages must follow JSON-RPC 2.0. Responses must contain exactly one of `result` or `error`, and notifications must not include an id: https://modelcontextprotocol.io/specification/2025-06-18/basic/index
- Lifecycle starts with `initialize`; after a successful initialize response, the client sends `notifications/initialized`: https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle
- `InitializeResult` must contain `protocolVersion`, `capabilities`, and `serverInfo`: https://modelcontextprotocol.io/specification/2025-06-18/schema
- `tools/list` returns a `tools` array; each tool has `name` and required `inputSchema`: https://modelcontextprotocol.io/specification/2025-06-18/schema
- Stdio transport uses newline-delimited UTF-8 JSON-RPC messages. Streamable HTTP uses POST/GET and requires clients to accept both `application/json` and `text/event-stream` for POST responses: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports

The MCP Python SDK provides the client transports used by remote probing:

- `streamablehttp_client` for Streamable HTTP MCP servers.
- `sse_client` for SSE MCP servers.
- `ClientSession.initialize`, `send_ping`, `list_tools`, `list_prompts`, and `list_resources`.

APD only calls `list_prompts` or `list_resources` when the initialized server advertises those capabilities.

Source: https://github.com/modelcontextprotocol/python-sdk

## Deliberate Limits

This PR does not claim real-world app integration testing. Driving actual Claude Desktop, Claude Code, Codex, Cursor, Cline, Roo Code, Zed, OpenCode, and Windsurf installations belongs in a separate opt-in integration harness because those apps are not reliably available in GitHub Actions.

## Packaging Sources

The installation and release flow follows Python CLI packaging conventions from official sources:

- pipx installs and runs apps from Python packages in isolated environments and works on macOS, Linux, and Windows: https://pipx.pypa.io/latest/docs/ and https://pipx.pypa.io/latest/installation/
- uv supports `uv tool install` for persistent command-line tools and `uvx` for one-off tool execution in isolated environments: https://docs.astral.sh/uv/concepts/tools/
- PyPI Trusted Publishing with GitHub Actions avoids storing PyPI API tokens in repository secrets and requires `id-token: write` for the publish job: https://docs.pypi.org/trusted-publishers/using-a-publisher/
- `pypa/gh-action-pypi-publish` is the PyPA-supported publishing action and recommends building distributions in a separate job before publishing: https://github.com/marketplace/actions/pypi-publish
- The `mcp-doctor` PyPI name is already occupied, so this project keeps the package name `agent-plugin-diagnostics` while still exposing the `apd` and `mcp-doctor` commands: https://pypi.org/project/mcp-doctor/
