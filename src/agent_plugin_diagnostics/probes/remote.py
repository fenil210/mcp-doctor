from __future__ import annotations

import asyncio
from typing import Any

from agent_plugin_diagnostics.core.models import ServerConfig, Transport
from agent_plugin_diagnostics.probes.stdio import ProbeResult


def probe_remote_server(server: ServerConfig, timeout: float = 10.0) -> ProbeResult:
    if server.transport not in {Transport.HTTP, Transport.SSE} or not server.url:
        return ProbeResult(server_id=server.id, ok=False, error="server is not a remote server")
    try:
        return asyncio.run(_probe_remote_server(server, timeout))
    except Exception as error:
        return ProbeResult(server_id=server.id, ok=False, error=str(error))


async def _probe_remote_server(server: ServerConfig, timeout: float) -> ProbeResult:
    try:
        import httpx
        from mcp import ClientSession
        from mcp.client.sse import sse_client
        from mcp.client.streamable_http import streamable_http_client
    except ImportError:
        return ProbeResult(
            server_id=server.id,
            ok=False,
            error="remote probing requires the mcp package to be installed",
        )

    if not server.url:
        return ProbeResult(server_id=server.id, ok=False, error="remote server URL is missing")

    if server.transport == Transport.SSE:
        async with sse_client(
            server.url,
            headers=server.headers or None,
            timeout=timeout,
            sse_read_timeout=timeout,
        ) as streams:
            return await _probe_streams(server, streams[0], streams[1], timeout, ClientSession)

    async with (
        httpx.AsyncClient(headers=server.headers or None, timeout=timeout) as http_client,
        streamable_http_client(server.url, http_client=http_client) as streams,
    ):
        return await _probe_streams(server, streams[0], streams[1], timeout, ClientSession)


async def _probe_streams(
    server: ServerConfig,
    read_stream: Any,
    write_stream: Any,
    timeout: float,
    session_class: Any,
) -> ProbeResult:
    async with session_class(read_stream, write_stream) as session:
        initialize_result = await asyncio.wait_for(session.initialize(), timeout=timeout)
        await asyncio.wait_for(session.send_ping(), timeout=timeout)
        tools_result = await asyncio.wait_for(session.list_tools(), timeout=timeout)
        schema_error = _find_sdk_tool_schema_error(tools_result.tools)
        if schema_error:
            return ProbeResult(server_id=server.id, ok=False, error=schema_error)
        prompts: tuple[str, ...] = ()
        resources: tuple[str, ...] = ()
        capabilities = getattr(initialize_result, "capabilities", None)
        if getattr(capabilities, "prompts", None) is not None:
            prompt_result = await asyncio.wait_for(session.list_prompts(), timeout=timeout)
            prompts = tuple(prompt.name for prompt in prompt_result.prompts)
        if getattr(capabilities, "resources", None) is not None:
            resource_result = await asyncio.wait_for(session.list_resources(), timeout=timeout)
            resources = tuple(str(resource.uri) for resource in resource_result.resources)
        server_info = getattr(initialize_result, "serverInfo", None)
        server_name = getattr(server_info, "name", None) if server_info else None
        protocol_version = getattr(initialize_result, "protocolVersion", None)
        return ProbeResult(
            server_id=server.id,
            ok=True,
            tools=tuple(tool.name for tool in tools_result.tools),
            prompts=prompts,
            resources=resources,
            protocol_version=str(protocol_version) if protocol_version else None,
            server_name=str(server_name) if server_name else None,
            ping_ok=True,
        )


def _find_sdk_tool_schema_error(tools: Any) -> str | None:
    for tool in tools:
        name = getattr(tool, "name", None)
        if not isinstance(name, str) or not name:
            return "tools/list returned a tool without a string name"
        schema = getattr(tool, "inputSchema", None)
        if schema is not None and not isinstance(schema, dict):
            return f"tool {name} has invalid inputSchema"
    return None
