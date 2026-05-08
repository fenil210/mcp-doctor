from __future__ import annotations

import asyncio
from typing import Any

from agent_plugin_diagnostics.core.models import ServerConfig, Transport
from agent_plugin_diagnostics.probes.protocol import (
    validate_resources_result,
    validate_tools_result,
)
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
        tool_dicts = [_sdk_tool_to_dict(tool) for tool in tools_result.tools]
        tool_names, schema_error = validate_tools_result({"tools": tool_dicts})
        if schema_error:
            return ProbeResult(
                server_id=server.id,
                ok=False,
                error=schema_error,
                failure_rule_id="APD081",
            )
        prompts: tuple[str, ...] = ()
        resources: tuple[str, ...] = ()
        capabilities = getattr(initialize_result, "capabilities", None)
        if getattr(capabilities, "prompts", None) is not None:
            prompt_result = await asyncio.wait_for(session.list_prompts(), timeout=timeout)
            prompts = tuple(prompt.name for prompt in prompt_result.prompts)
        if getattr(capabilities, "resources", None) is not None:
            resource_result = await asyncio.wait_for(session.list_resources(), timeout=timeout)
            resources, schema_error = validate_resources_result(
                {
                    "resources": [
                        {"uri": str(resource.uri)} for resource in resource_result.resources
                    ]
                }
            )
            if schema_error:
                return ProbeResult(
                    server_id=server.id,
                    ok=False,
                    error=schema_error,
                    failure_rule_id="APD081",
                )
        server_info = getattr(initialize_result, "serverInfo", None)
        server_name = getattr(server_info, "name", None) if server_info else None
        protocol_version = getattr(initialize_result, "protocolVersion", None)
        return ProbeResult(
            server_id=server.id,
            ok=True,
            tools=tool_names,
            prompts=prompts,
            resources=resources,
            protocol_version=str(protocol_version) if protocol_version else None,
            server_name=str(server_name) if server_name else None,
            ping_ok=True,
        )


def _sdk_tool_to_dict(tool: Any) -> dict[str, Any]:
    value: dict[str, Any] = {"name": getattr(tool, "name", None)}
    input_schema = getattr(tool, "inputSchema", None)
    if input_schema is None:
        input_schema = getattr(tool, "input_schema", None)
    if input_schema is not None:
        value["inputSchema"] = input_schema
    output_schema = getattr(tool, "outputSchema", None)
    if output_schema is None:
        output_schema = getattr(tool, "output_schema", None)
    if output_schema is not None:
        value["outputSchema"] = output_schema
    annotations = getattr(tool, "annotations", None)
    if annotations is not None:
        value["annotations"] = annotations
    metadata = getattr(tool, "_meta", None)
    if metadata is not None:
        value["_meta"] = metadata
    return value
