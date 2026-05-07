from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from agent_plugin_diagnostics.core.models import (
    ClientConfig,
    ConfigSource,
    Finding,
    ServerConfig,
    Severity,
    Transport,
)


def invalid_config_finding(source: ConfigSource, error: Exception) -> Finding:
    return Finding(
        id="APD001",
        title="Invalid configuration file",
        severity=Severity.HIGH,
        category="configuration",
        message=f"{source.path} could not be parsed as {source.format}: {error}",
        suggestion="Fix the syntax error or regenerate the client configuration.",
        source=source,
        evidence=str(error),
    )


def no_servers_finding(source: ConfigSource) -> Finding:
    return Finding(
        id="APD002",
        title="No server definitions found",
        severity=Severity.LOW,
        category="configuration",
        message=f"{source.path} does not contain supported MCP server definitions.",
        suggestion="Add server definitions under mcpServers or servers.",
        source=source,
    )


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")
    return data


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise ValueError("top-level TOML value must be a table")
    return data


def normalize_transport(entry: Mapping[str, Any]) -> Transport:
    raw_type = str(entry.get("type") or entry.get("transport") or "").lower()
    if raw_type in {"http", "streamable-http", "streamable_http"}:
        return Transport.HTTP
    if raw_type == "sse":
        return Transport.SSE
    if raw_type == "stdio":
        return Transport.STDIO
    if entry.get("url") or entry.get("serverUrl"):
        url = str(entry.get("url") or entry.get("serverUrl"))
        return Transport.SSE if "/sse" in url.lower() else Transport.HTTP
    if entry.get("command"):
        return Transport.STDIO
    return Transport.UNKNOWN


def normalize_server(
    server_id: str,
    entry: Mapping[str, Any],
    source: ConfigSource,
) -> ServerConfig:
    args = entry.get("args") or ()
    if not isinstance(args, list):
        args = ()
    env = entry.get("env") or {}
    if not isinstance(env, dict):
        env = {}
    headers = (
        entry.get("headers") or entry.get("http_headers") or entry.get("env_http_headers") or {}
    )
    if not isinstance(headers, dict):
        headers = {}
    enabled = entry.get("enabled", True)
    if not isinstance(enabled, bool):
        enabled = True
    return ServerConfig(
        id=server_id,
        source=source,
        transport=normalize_transport(entry),
        command=str(entry["command"]) if entry.get("command") is not None else None,
        args=tuple(str(arg) for arg in args),
        env={str(key): str(value) for key, value in env.items()},
        url=str(entry.get("url") or entry.get("serverUrl"))
        if entry.get("url") or entry.get("serverUrl")
        else None,
        headers={str(key): str(value) for key, value in headers.items()},
        cwd=str(entry["cwd"]) if entry.get("cwd") is not None else None,
        enabled=enabled,
        raw=dict(entry),
    )


def parse_server_map(source: ConfigSource, data: Mapping[str, Any], key: str) -> ClientConfig:
    raw_servers = data.get(key) or {}
    if not isinstance(raw_servers, dict):
        raw_servers = {}
    servers: list[ServerConfig] = []
    for server_id, entry in raw_servers.items():
        if isinstance(entry, dict):
            servers.append(normalize_server(str(server_id), entry, source))
    return ClientConfig(source=source, servers=tuple(servers))


def parse_vscode_servers(source: ConfigSource, data: Mapping[str, Any]) -> ClientConfig:
    raw_servers = data.get("servers") or {}
    if not isinstance(raw_servers, dict):
        raw_servers = {}
    servers: list[ServerConfig] = []
    for server_id, entry in raw_servers.items():
        if isinstance(entry, dict):
            servers.append(normalize_server(str(server_id), entry, source))
    return ClientConfig(source=source, servers=tuple(servers))


def parse_codex_servers(source: ConfigSource, data: Mapping[str, Any]) -> ClientConfig:
    raw_servers = data.get("mcp_servers") or {}
    if not isinstance(raw_servers, dict):
        raw_servers = {}
    servers: list[ServerConfig] = []
    for server_id, entry in raw_servers.items():
        if isinstance(entry, dict):
            servers.append(normalize_server(str(server_id), entry, source))
    return ClientConfig(source=source, servers=tuple(servers))
