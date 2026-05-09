# Architecture

Agent Plugin Diagnostics is organized around a small domain model and separate edge modules.

## Flow

```mermaid
flowchart LR
    CLI["CLI or MCP tool"] --> Discovery["Client adapters"]
    Discovery --> Model["Normalized config model"]
    Model --> Checks["Static checks"]
    Model --> Probes["Controlled probes"]
    Model --> Integrations["Real app integrations"]
    Checks --> Report["Report renderers"]
    Probes --> Report
    Integrations --> Report
```

## Modules

`core`

Domain models, rule metadata, utility functions, and workflow orchestration.

`clients`

Client-specific discovery and parsing for Claude Code, Codex, Cursor, VS Code, and Windsurf.

`checks`

Deterministic checks that inspect normalized configs and emit findings.

`probes`

Controlled MCP protocol probes. Probes run initialize, initialized notification, ping, tools/list, and optional prompts/resources lists when the server advertises those capabilities. The protocol validator checks JSON-RPC 2.0 response envelopes, initialize result shape, negotiated protocol version, empty ping result shape, and list result schemas. Remote HTTP and SSE probes are opt-in through `apd probe --remote`.

`reports`

Terminal, JSON, Markdown, and SARIF renderers. Secret redaction happens before machine-readable report output.

`fixers`

Fix-plan generation and safe patch application. Fix mode is dry-run by default, writes only exact file patches, and creates backup files before applying changes.

`integrations`

Read-only real app detection. The integration harness checks documented config paths, detects known app commands on `PATH` or documented installer paths, optionally runs version commands with timeouts, and reports what APD actually observed on the current machine.

`mcp_server`

Optional MCP server mode built on the official Python MCP SDK. The package installs this surface through the `mcp` extra.

## Extension Points

Add a client by implementing `ClientAdapter`.

Add a check by returning findings from a class that satisfies the `Check` protocol.

Add a report format by creating a renderer that consumes `DiagnosticReport`.

The CLI and MCP server should stay thin. They should call workflow functions rather than owning diagnostic behavior.
