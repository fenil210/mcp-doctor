from __future__ import annotations

import json
from typing import Any

from agent_plugin_diagnostics.core.models import ServerConfig, Transport

SUPPORTED_CLIENTS = ("claude-code", "codex", "cursor", "vscode", "windsurf")


def doctor_server_snippet(client: str) -> str:
    server = {
        "command": "apd",
        "args": ["serve-mcp"],
    }
    if client == "codex":
        return _toml_server("mcp-doctor", server)
    if client == "vscode":
        return _json({"servers": {"mcp-doctor": {"type": "stdio", **server}}})
    if client in {"claude-code", "cursor", "windsurf"}:
        return _json({"mcpServers": {"mcp-doctor": server}})
    raise ValueError(f"unsupported client: {client}")


def server_config_snippet(server: ServerConfig, client: str) -> str:
    entry = _server_entry(server, include_type=client == "vscode")
    if client == "codex":
        return _toml_server(server.id, entry)
    if client == "vscode":
        return _json({"servers": {server.id: entry}})
    if client in {"claude-code", "cursor", "windsurf"}:
        return _json({"mcpServers": {server.id: entry}})
    raise ValueError(f"unsupported client: {client}")


def _server_entry(server: ServerConfig, include_type: bool) -> dict[str, Any]:
    entry: dict[str, Any] = {}
    if include_type:
        entry["type"] = server.transport.value if server.transport != Transport.UNKNOWN else "stdio"
    if server.command:
        entry["command"] = server.command
    if server.args:
        entry["args"] = list(server.args)
    if server.cwd:
        entry["cwd"] = server.cwd
    if server.env:
        entry["env"] = dict(server.env)
    if server.url:
        entry["url"] = server.url
    if server.headers:
        entry["headers"] = dict(server.headers)
    return entry


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _toml_server(server_id: str, entry: dict[str, Any]) -> str:
    lines = [f"[mcp_servers.{_toml_key(server_id)}]"]
    for key, value in entry.items():
        lines.append(f"{key} = {_toml_value(value)}")
    return "\n".join(lines) + "\n"


def _toml_key(value: str) -> str:
    if value.replace("_", "").replace("-", "").isalnum():
        return value
    return json.dumps(value)


def _toml_value(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        items = ", ".join(
            f"{_toml_key(str(key))} = {_toml_value(item)}" for key, item in value.items()
        )
        return "{ " + items + " }"
    raise TypeError(f"unsupported TOML value type: {type(value).__name__}")
