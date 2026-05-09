# Agent Plugin Diagnostics

Working name: Agent Plugin Diagnostics
Package name: agent-plugin-diagnostics
CLI name: apd

This document is the product and technical direction for a Python-first open source project that helps developers audit, debug, repair, and share MCP and AI coding-agent plugin setups across tools such as Claude Code, Codex, Cursor, VS Code, and Windsurf.

The project should be useful as a normal CLI, as a CI check, and as an MCP server that agents can call when they need to understand their own tool setup.

## Problem

Developers are rapidly adding MCP servers, skills, plugins, hooks, and agent rules to their local coding environments. The ecosystem is powerful, but the operational surface is fragmented:

- Each client stores MCP configuration in a different location and format.
- A setup can work in one client but fail silently in another.
- Stdio servers often depend on local binaries, package managers, working directories, and environment variables that are not visible from the agent UI.
- Project-scoped configs are often copied into repositories without clear security boundaries.
- Remote MCP servers introduce auth, transport, timeout, and permission issues.
- Existing tools focus on one slice: protocol inspection, security scanning, config syncing, or server compliance.

The missing piece is a local-first diagnostic and repair layer for the whole developer agent stack.

## Goal

Build a Python tool that answers one practical question:

Why is my agent plugin or MCP setup broken, risky, or non-portable, and what exactly should I change?

The first public version should be able to:

- Discover MCP and plugin configuration from multiple agent clients.
- Normalize those configs into one internal model.
- Detect broken local commands, missing files, missing environment variables, risky package invocations, unpinned versions, duplicate server names, and client-specific incompatibilities.
- Probe configured MCP servers where safe.
- Produce readable terminal, JSON, SARIF, and Markdown reports.
- Generate fix instructions and client-specific config snippets.
- Expose the same diagnostics as an MCP server so Claude Code, Codex, Cursor, or VS Code can ask for help directly.

## Non-Goals

The project will not try to be a full MCP gateway in the first version.

It will not execute arbitrary untrusted tool calls beyond controlled handshake and discovery probes.

It will not become a SaaS product or require cloud accounts.

It will not replace MCP Inspector, security scanners, or client-native plugin systems.

It will not auto-edit user configuration without an explicit command and a previewable diff.

## Target Users

Primary users:

- Developers using Claude Code, Codex, Cursor, VS Code, Windsurf, or similar tools with MCP servers.
- MCP server authors who want their installation docs to work across clients.
- Open source maintainers who want contributors to debug setup issues faster.

Secondary users:

- Teams standardizing AI coding tool configuration.
- Security-minded developers who want local visibility before installing unknown MCP servers.
- Plugin authors who want compatibility reports for Claude Code and Codex plugin bundles.

## Why This Should Exist

MCP is now the common integration layer across major agent clients. The official MCP docs describe MCP as an open standard for connecting AI applications to external systems, and the official SDKs support servers, clients, tools, resources, prompts, and local or remote transports.

Claude Code supports plugin-provided MCP servers and project, local, and user MCP scopes.

Codex supports MCP server definitions in configuration and Codex plugins can bundle `.mcp.json` files.

Cursor supports MCP through project and global `mcp.json` files with stdio, SSE, and Streamable HTTP transports.

VS Code supports workspace `.vscode/mcp.json`, user-profile MCP configuration, install URLs, and extension-based registration.

Windsurf supports MCP configuration through `mcp_config.json` and supports stdio, HTTP, and SSE transports.

This creates a real compatibility matrix. A practical tool should inspect that matrix instead of assuming every client behaves the same.

## Prior Art

This project should respect existing work and avoid copying its lane.

MCP Inspector:

- Strong for interactive protocol testing and debugging one server.
- Not focused on cross-client local config inventory, repository portability, or fix generation.

mcp-scan, mcp-auditor, MCP security scanners:

- Strong for security scanning, static checks, dynamic adversarial tests, or runtime monitoring.
- Not primarily focused on developer setup repair across Claude Code, Codex, Cursor, VS Code, and Windsurf.

Existing mcp-doctor projects:

- The name is already used by several tools and packages.
- Some focus on server quality or protocol compliance.
- This project should avoid the `mcp-doctor` name and be broader than server health checks.

Conductor and similar config-sync tools:

- Strong for managing or syncing MCP config across clients.
- This project should diagnose, explain, and validate before it manages or syncs anything.

The differentiator is local-first, multi-client diagnostics with a contributor-friendly Python architecture and agent-callable output.

## Product Shape

The project has three surfaces.

1. CLI

The CLI is the primary developer experience.

Initial commands:

```bash
apd scan
apd audit
apd probe
apd integrations
apd explain <finding-id>
apd export --format markdown
apd export --format json
apd export --format sarif
apd init --client cursor
apd init --client codex
apd serve-mcp
```

2. Python Library

The library should expose stable domain APIs for discovery, parsing, checks, reports, and fix planning.

Example package areas:

```text
agent_plugin_diagnostics/
  core/
  clients/
  checks/
  probes/
  reports/
  fixers/
  mcp_server/
```

3. MCP Server

The MCP server exposes read-only diagnostic tools at first.

Candidate tools:

- `scan_agent_stack(root_path: str | None)`.
- `audit_agent_stack(root_path: str | None, policy: str | None)`.
- `explain_finding(finding_id: str)`.
- `generate_client_config(server_id: str, client: str)`.
- `list_supported_clients()`.

## Supported Clients

Version 0.1 should target:

- Claude Code project `.mcp.json`.
- Claude Code user and local config discovery where feasible.
- Codex `~/.codex/config.toml`.
- Cursor `.cursor/mcp.json` and `~/.cursor/mcp.json`.
- VS Code `.vscode/mcp.json`.
- Windsurf `~/.codeium/windsurf/mcp_config.json`.

Version 0.2 can add:

- Claude Desktop config.
- Cline and Roo Code config.
- Zed config.
- OpenCode config.
- Gemini CLI or Antigravity config if stable enough.

## Initial Checks

Configuration checks:

- Invalid JSON or TOML.
- Unknown top-level keys for a client.
- Missing required fields.
- Duplicate server names.
- Disabled servers that are still referenced by generated docs.
- Project config that contains literal secrets.
- Environment variables referenced but not available.
- Relative paths that are invalid for the client.
- Absolute paths that reduce portability.
- Path variables unsupported by the target client.

Command checks:

- Command not found.
- `npx`, `uvx`, `pipx`, `python`, `node`, or `docker` not available.
- Unpinned packages using `latest`.
- Package-manager commands that run arbitrary install scripts.
- Server working directory missing.
- Arguments referencing missing files.
- Windows path issues.

Transport checks:

- Stdio config shape valid.
- HTTP or SSE URL valid.
- Auth headers contain placeholders instead of secrets.
- Timeout values absent or too aggressive.
- Client does not support a configured transport or option.

Protocol checks:

- Server starts within timeout.
- Initialize handshake succeeds.
- Client sends the current MCP protocol version.
- Client sends `notifications/initialized` after successful initialize.
- JSON-RPC responses use valid envelopes with matching ids and exactly one of result or error.
- Tools list succeeds.
- Prompt list succeeds where supported.
- Resource list succeeds where supported.
- Tool schemas include required `inputSchema` objects with `type: object`.
- Server output does not leak obvious secrets during discovery.

Security and trust checks:

- Literal tokens in config files.
- Overbroad filesystem server roots.
- Shell execution tools exposed by unknown packages.
- Remote URLs over plain HTTP.
- GitHub shorthand or package names that are not pinned.
- Suspicious typosquatting indicators for common MCP packages.
- Tool names that collide across servers.
- Tool descriptions with suspicious instruction patterns.

Portability checks:

- Config works only for one client because of unsupported interpolation syntax.
- Local paths that cannot work on another OS.
- Missing installation instructions for required runtime.
- Project config requires user-private paths.
- Server name uses characters unsupported by at least one target client.

## Report Model

Every finding should have:

- Stable finding id.
- Severity: info, low, medium, high, critical.
- Category.
- Affected client.
- Affected config path.
- Server id.
- Exact evidence.
- Explanation in plain language.
- Suggested fix.
- Machine-readable metadata.

The report should support:

- Terminal summary.
- Markdown report for issues and PRs.
- JSON for tooling.
- SARIF for GitHub code scanning.

## Fix Strategy

The project should separate finding generation from fixing.

Version 0.1 starts with fix plans and narrowly scoped safe fix commands:

```bash
apd fix --finding APD001
apd fix --all --dry-run
```

Fixes must be previewed before writing. The implementation should preserve formatting where reasonable, create backups before applying, and avoid rewriting unrelated parts of user config.

## Architecture Principles

Use SOLID principles without turning the project into abstraction theater.

Single Responsibility:

- Client adapters only locate and parse client-specific configs.
- Checks only inspect normalized models and return findings.
- Probes only execute controlled protocol discovery.
- Reporters only transform results into output formats.
- Fixers only produce or apply config changes.

Open Closed:

- New clients should be added by implementing a client adapter.
- New checks should be added without changing the check runner.
- New report formats should be added without changing checks.

Liskov Substitution:

- Every client adapter should satisfy the same interface.
- Test fixtures should be able to run the same checks against all adapters.

Interface Segregation:

- Do not force every adapter to support writing, probing, or plugin discovery.
- Keep read-only discovery separate from mutation.

Dependency Inversion:

- Core logic depends on interfaces and domain models.
- CLI, filesystem, process execution, and MCP SDK details stay at the edges.

## Engineering Standards

Python:

- Python 3.11 or newer.
- `uv` for local development.
- `pyproject.toml` as the single package configuration.
- `ruff` for linting and formatting.
- `mypy` or `pyright` for type checking.
- `pytest` for tests.
- `typer` or `argparse` for CLI. Prefer Typer only if the dependency cost is worth it.
- `pydantic` only for boundary validation and report models, not for every internal object.

Code style:

- Clear names over comments.
- Comments only for non-obvious logic.
- Docstrings only for public APIs or behavior that needs generated documentation.
- No decorative output.
- No emojis in code, docs, CLI output, issues, or release notes.
- Avoid global mutable state.
- Avoid shell string construction when structured process execution is available.

Testing:

- Unit tests for every adapter and check.
- Golden fixtures for client config parsing.
- Probe tests using small local fake MCP servers.
- Integration harness tests using temporary config files and fake commands on PATH.
- Snapshot tests for Markdown, JSON, and SARIF output.
- Windows path tests.
- CI on Windows, macOS, and Linux.

Security:

- Local-first by default.
- No telemetry.
- No network calls unless a user asks to probe a remote server or update package metadata.
- Redact secrets in logs and reports.
- Never print full environment values.
- Process execution must use explicit argv arrays.
- Probe mode must use timeouts and cleanup child processes.
- Real app integration checks must be read-only and must not launch GUI apps.

## Repository Structure

Proposed after approval:

```text
.
  README.md
  features.md
  pyproject.toml
  LICENSE
  CONTRIBUTING.md
  SECURITY.md
  src/
    agent_plugin_diagnostics/
      __init__.py
      cli.py
      core/
      clients/
      checks/
      probes/
      reports/
      fixers/
      mcp_server/
  tests/
    fixtures/
      claude/
      codex/
      cursor/
      vscode/
      windsurf/
    unit/
    integration/
  docs/
    architecture.md
    client-matrix.md
    rule-index.md
  .github/
    workflows/
      ci.yml
```

## Milestones

Milestone 0: Product and repo foundation

- Approve this `features.md`.
- Pick final project name.
- Create public GitHub repository.
- Add README, license, contributing guide, security policy, and issue templates.

Milestone 1: Read-only config discovery

- Implement normalized config model.
- Implement Cursor, Codex, Claude Code project, VS Code, and Windsurf adapters.
- Add parser fixtures and tests.
- Add `apd scan --format terminal|json`.

Milestone 2: Static checks and reports

- Implement the first 20 checks.
- Add severity model and stable finding ids.
- Add Markdown export.
- Add SARIF export.

Milestone 3: Controlled MCP probing

- Add stdio server startup probe.
- Add initialize and list-tools checks.
- Add timeout and cleanup handling.
- Add fake MCP server fixtures.

Milestone 4: MCP server mode

- Expose scan and explain tools via MCP.
- Add installation snippets for Claude Code, Codex, Cursor, VS Code, and Windsurf.
- Add smoke tests with MCP Inspector.

Milestone 5: Fix planning

- Generate safe, client-specific fix plans.
- Add dry-run diff output.
- Avoid automatic writes until enough test coverage exists.

## Contributor Strategy

The project should be easy to contribute to.

Good first contributions:

- Add a fixture for a client config.
- Add a new check.
- Add a client adapter.
- Improve a finding explanation.
- Add docs for a specific MCP client.

Contributor docs should explain:

- How adapters work.
- How checks are registered.
- How finding ids are assigned.
- How fixtures are structured.
- How to run the test suite.
- How to add a new client without touching core logic.

## Open Questions

Project name:

- `mcp-doctor` is already taken.
- `Agent Plugin Diagnostics` is descriptive but not final.
- Before publishing, choose a name that is not already used on GitHub or PyPI.

License:

- MIT is simple and friendly.
- Apache 2.0 gives explicit patent language.
- Recommendation: Apache 2.0 if the project may grow into a serious security-adjacent tool.

Package manager:

- Recommendation: use `uv` for development and support `pipx` or `uvx` installation for users.

CLI dependency:

- Typer gives a good CLI quickly.
- Argparse keeps dependencies smaller.
- Recommendation: Typer for developer experience unless we decide zero-extra dependencies matter more.

## Source Notes

The following public docs informed this plan:

- MCP official docs: https://modelcontextprotocol.io/docs/getting-started/intro
- MCP official SDK docs: https://modelcontextprotocol.io/docs/sdk
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- MCP Inspector docs: https://modelcontextprotocol.io/docs/tools/inspector
- MCP security best practices: https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices
- Claude Code MCP docs: https://code.claude.com/docs/en/mcp
- Claude Code plugin docs: https://code.claude.com/docs/en/plugins
- Claude Code plugin marketplace docs: https://code.claude.com/docs/en/plugin-marketplaces
- Codex MCP configuration reference: https://developers.openai.com/codex/config-reference
- Codex plugin build docs: https://developers.openai.com/codex/plugins/build
- Cursor MCP docs: https://docs.cursor.com/advanced/model-context-protocol
- VS Code MCP configuration reference: https://code.visualstudio.com/docs/copilot/reference/mcp-configuration
- VS Code MCP developer guide: https://code.visualstudio.com/api/extension-guides/mcp
- Windsurf MCP docs: https://docs.windsurf.com/windsurf/cascade/mcp
- OWASP MCP security guidance: https://owasp.org/www-project-mcp-top-10/
