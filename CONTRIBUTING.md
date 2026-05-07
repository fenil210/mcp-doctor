# Contributing

Agent Plugin Diagnostics is intended to be easy to extend without touching unrelated core code. Small, focused pull requests are welcome.

## Local Setup

```bash
git clone https://github.com/fenil210/mcp-doctor.git
cd mcp-doctor
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev,mcp]"
```

On macOS and Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

## Quality Gates

Run these before opening a pull request:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src/agent_plugin_diagnostics
python -m pytest
```

## Adding a Client Adapter

Client adapters live in `src/agent_plugin_diagnostics/clients`.

1. Implement the `ClientAdapter` protocol.
2. Locate only the config files owned by that client.
3. Parse into `ClientConfig` and `ServerConfig`.
4. Return parse errors as findings instead of raising through the CLI.
5. Add the adapter to `default_adapters`.
6. Add a fixture under `tests/fixtures`.
7. Add unit tests for discovery and parsing.

Adapters should not run commands, mutate files, or perform security checks. Their only job is discovery and normalization.

## Adding a Check

Checks live in `src/agent_plugin_diagnostics/checks`.

1. Add a stable rule in `core/rules.py`.
2. Implement the check against the normalized domain model.
3. Return `Finding` objects with exact evidence and suggested fixes.
4. Register the check through `default_checks`.
5. Add tests that prove both positive and negative cases.
6. Update `docs/rule-index.md`.

Checks should be deterministic and local-first. They should not make network calls.

## Finding IDs

Use the next available id in the relevant group:

- `APD00x`: parser and discovery problems.
- `APD01x`: configuration shape and runtime launcher problems.
- `APD02x`: environment and secret handling.
- `APD03x`: supply-chain and transport checks.
- `APD04x`: client interpolation and compatibility.
- `APD05x`: portability.
- `APD06x`: security boundaries.
- `APD07x`: duplicate names and usability.
- `APD08x`: controlled probe failures.

## Pull Request Checklist

- The change is scoped to one behavior or one extension point.
- Tests cover the new behavior.
- Documentation is updated when public behavior changes.
- No secrets, tokens, local private paths, telemetry, or network-only assumptions are introduced.
