# MCP Doctor

MCP Doctor is the repository for Agent Plugin Diagnostics, a Python-first toolkit for auditing MCP and AI coding-agent plugin setups across Claude Code, Codex, Cursor, VS Code, and Windsurf.

It helps answer a practical question: why is my agent plugin setup broken, risky, or non-portable, and what should I change?

## Why This Exists

MCP Doctor is not another MCP server and it is not a thin toy wrapper. It is a local diagnostics CLI for developers using MCP across Claude, Codex, Cursor, VS Code, Windsurf, Zed, Cline, Roo Code, and OpenCode.

It discovers real MCP configs from those clients, normalizes them into one model, and checks for broken commands, missing environment variables, literal secrets, unpinned package launches, broad filesystem roots, absolute local paths, duplicate server names, plain HTTP remote servers, and protocol compliance issues.

It can also run controlled MCP probes for initialize, initialized notification, ping, tools/list, prompts/list, and resources/list. Reports can be generated for terminal, JSON, Markdown, and SARIF workflows. Safe config fixes are previewed before writing and create backups when applied.

The practical value is simple: when someone says, "my MCP setup works on my machine but not yours," MCP Doctor gives them a concrete report instead of a guessing session.

## What It Does

- Discovers MCP configuration across supported local clients.
- Normalizes server definitions into one report model.
- Detects missing commands, missing env vars, literal secrets, risky package invocations, plain HTTP URLs, broad filesystem roots, absolute project paths, and duplicate server names.
- Runs controlled MCP probes for initialize, initialized notification, ping, tools/list, advertised prompts/list, and advertised resources/list.
- Validates MCP probe responses against JSON-RPC 2.0 envelope rules and required MCP result shapes.
- Checks real installed agent apps and documented config paths with an opt-in local integration harness.
- Exports terminal, JSON, Markdown, and SARIF reports.
- Runs as an optional MCP server so agents can ask for diagnostics directly.

## Install

From GitHub:

```bash
python -m pip install "agent-plugin-diagnostics @ git+https://github.com/fenil210/mcp-doctor.git"
```

For isolated CLI usage:

```bash
pipx install "agent-plugin-diagnostics @ git+https://github.com/fenil210/mcp-doctor.git"
```

For local development:

```bash
git clone https://github.com/fenil210/mcp-doctor.git
cd mcp-doctor
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev,mcp]"
```

On macOS and Linux, activate with `source .venv/bin/activate`.

## Quick Start

Scan the current workspace:

```bash
apd scan
```

Run checks:

```bash
apd audit
```

Preview safe config fixes:

```bash
apd fix --dry-run
```

Apply applicable fixes with backup files:

```bash
apd fix --apply
```

Write a Markdown report:

```bash
apd export --format markdown --output apd-report.md
```

Probe a stdio server:

```bash
apd probe --server filesystem
```

Include remote Streamable HTTP or SSE servers:

```bash
apd probe --remote --timeout 10
```

Check installed agent apps and real config files:

```bash
apd integrations
apd integrations --format json
apd integrations --no-version
```

Explain a finding:

```bash
apd explain APD021
```

Generate a client snippet that installs MCP Doctor as an MCP server:

```bash
apd init --client codex
apd init --client cursor
```

## Supported Clients

| Client | Configs |
| --- | --- |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json`, `~/AppData/Roaming/Claude/claude_desktop_config.json` |
| Claude Code | `.mcp.json`, `~/.claude.json` |
| Cline | `~/.cline/data/settings/cline_mcp_settings.json` |
| Codex | `.codex/config.toml`, `~/.codex/config.toml` |
| Cursor | `.cursor/mcp.json`, `~/.cursor/mcp.json` |
| OpenCode | `opencode.json`, `~/.config/opencode/opencode.json` |
| Roo Code | `.roo/mcp.json` |
| VS Code | `.vscode/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json`, `~/.codeium/mcp_config.json` |
| Zed | `.zed/settings.json`, `~/.config/zed/settings.json`, `~/.zed/settings.json`, `~/AppData/Roaming/Zed/settings.json` |

See [docs/client-matrix.md](docs/client-matrix.md) for details.

## Report Formats

Terminal output is designed for local debugging.

JSON output is designed for scripts and agent workflows.

Markdown output is designed for issues, pull requests, and setup documentation.

SARIF output is designed for GitHub code scanning and CI surfaces.

```bash
apd audit --format json
apd audit --format sarif --output apd.sarif
```

## Real App Integration Harness

`apd integrations` checks the actual machine instead of assuming apps exist. It looks for documented config files, checks known CLI commands on `PATH`, optionally runs version commands with a timeout, and reuses the normal APD audit model for parsed config and server counts.

The harness is read-only. It does not launch GUI apps, edit configuration, install packages, or run configured MCP servers. Use `apd probe` separately when you want controlled MCP server startup checks.

## MCP Server Mode

Install with the MCP extra:

```bash
python -m pip install -e ".[mcp]"
```

Run:

```bash
apd serve-mcp
```

Available MCP tools:

- `scan_agent_stack`
- `audit_agent_stack`
- `explain_finding`
- `generate_client_config`
- `list_supported_clients`

Generate client config snippets with:

```bash
apd init --client claude-code
apd init --client claude-desktop
apd init --client cline
apd init --client codex
apd init --client cursor
apd init --client opencode
apd init --client roo-code
apd init --client vscode
apd init --client windsurf
apd init --client zed
```

## Development

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src/agent_plugin_diagnostics
python -m pytest
```

Project plan: [features.md](features.md)

Architecture: [docs/architecture.md](docs/architecture.md)

Rules: [docs/rule-index.md](docs/rule-index.md)

Research notes: [docs/research-notes.md](docs/research-notes.md)

## Security Model

MCP Doctor is local-first and has no telemetry. Static checks do not make network calls. Probe mode starts configured stdio MCP servers only for controlled protocol checks. Remote HTTP and SSE probing requires `apd probe --remote` because it can make network requests. Protocol compliance checks are limited to the probe path APD actually exercises: initialize, initialized notification, ping, tools/list, and advertised prompt/resource listing.

Fix mode is dry-run by default. `apd fix --apply` only writes fixes that APD can express as exact file patches and creates `.apd.bak` backup files unless `--no-backup` is provided.

## License

Apache-2.0.
