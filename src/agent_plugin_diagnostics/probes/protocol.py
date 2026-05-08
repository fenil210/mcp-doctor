from __future__ import annotations

from typing import Any

from agent_plugin_diagnostics import __version__

CURRENT_PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
CLIENT_NAME = "mcp-doctor"


def initialize_request(request_id: int) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "initialize",
        "params": {
            "protocolVersion": CURRENT_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": CLIENT_NAME, "version": __version__},
        },
    }


def initialized_notification() -> dict[str, Any]:
    return {"jsonrpc": "2.0", "method": "notifications/initialized"}


def extract_success_result(
    message: Any,
    expected_id: int,
    context: str,
) -> tuple[Any, str | None]:
    envelope_error = validate_success_response_envelope(message, expected_id, context)
    if envelope_error:
        return None, envelope_error
    return message["result"], None


def validate_success_response_envelope(
    message: Any,
    expected_id: int,
    context: str,
) -> str | None:
    envelope_error = validate_response_envelope(message, expected_id, context)
    if envelope_error:
        return envelope_error
    if "error" in message:
        error = message["error"]
        return f"{context} returned JSON-RPC error {error['code']}: {error['message']}"
    return None


def validate_response_envelope(message: Any, expected_id: int, context: str) -> str | None:
    if not isinstance(message, dict):
        return f"{context} response must be a JSON object"
    if message.get("jsonrpc") != "2.0":
        return f"{context} response must set jsonrpc to 2.0"
    if message.get("id") != expected_id:
        return f"{context} response id must match request id {expected_id}"
    has_result = "result" in message
    has_error = "error" in message
    if has_result == has_error:
        return f"{context} response must contain exactly one of result or error"
    if has_error:
        error = message["error"]
        if not isinstance(error, dict):
            return f"{context} error response must contain an error object"
        if not isinstance(error.get("code"), int):
            return f"{context} error response must contain an integer error code"
        if not isinstance(error.get("message"), str) or not error["message"]:
            return f"{context} error response must contain a non-empty error message"
    return None


def validate_initialize_result(result: Any) -> str | None:
    if not isinstance(result, dict):
        return "initialize result must be an object"
    protocol_version = result.get("protocolVersion")
    if not isinstance(protocol_version, str) or not protocol_version:
        return "initialize result must contain a string protocolVersion"
    if protocol_version not in SUPPORTED_PROTOCOL_VERSIONS:
        return f"server negotiated unsupported MCP protocol version {protocol_version}"
    capabilities = result.get("capabilities")
    if not isinstance(capabilities, dict):
        return "initialize result must contain a capabilities object"
    server_info = result.get("serverInfo")
    if not isinstance(server_info, dict):
        return "initialize result must contain a serverInfo object"
    if not isinstance(server_info.get("name"), str) or not server_info["name"]:
        return "serverInfo must contain a non-empty string name"
    if not isinstance(server_info.get("version"), str) or not server_info["version"]:
        return "serverInfo must contain a non-empty string version"
    return None


def validate_empty_result(result: Any, context: str) -> str | None:
    if not isinstance(result, dict):
        return f"{context} result must be an object"
    return None


def validate_tools_result(result: Any) -> tuple[tuple[str, ...], str | None]:
    if not isinstance(result, dict):
        return (), "tools/list result must be an object"
    raw_tools = result.get("tools")
    if not isinstance(raw_tools, list):
        return (), "tools/list result must contain a tools array"
    names: list[str] = []
    for index, tool in enumerate(raw_tools):
        error = validate_tool(tool, index)
        if error:
            return (), error
        names.append(tool["name"])
    next_cursor = result.get("nextCursor")
    if next_cursor is not None and not isinstance(next_cursor, str):
        return (), "tools/list nextCursor must be a string when present"
    return tuple(names), None


def validate_tool(tool: Any, index: int = 0) -> str | None:
    if not isinstance(tool, dict):
        return f"tools/list entry {index} must be an object"
    name = tool.get("name")
    if not isinstance(name, str) or not name:
        return f"tools/list entry {index} must contain a non-empty string name"
    input_schema = tool.get("inputSchema")
    if input_schema is None:
        return f"tool {name} is missing required inputSchema"
    schema_error = _validate_object_schema(input_schema, f"tool {name} inputSchema")
    if schema_error:
        return schema_error
    output_schema = tool.get("outputSchema")
    if output_schema is not None:
        schema_error = _validate_object_schema(output_schema, f"tool {name} outputSchema")
        if schema_error:
            return schema_error
    annotations = tool.get("annotations")
    if annotations is not None and not isinstance(annotations, dict):
        return f"tool {name} annotations must be an object when present"
    metadata = tool.get("_meta")
    if metadata is not None and not isinstance(metadata, dict):
        return f"tool {name} _meta must be an object when present"
    return None


def validate_prompts_result(result: Any) -> tuple[tuple[str, ...], str | None]:
    if not isinstance(result, dict):
        return (), "prompts/list result must be an object"
    raw_prompts = result.get("prompts")
    if not isinstance(raw_prompts, list):
        return (), "prompts/list result must contain a prompts array"
    names: list[str] = []
    for index, prompt in enumerate(raw_prompts):
        if not isinstance(prompt, dict):
            return (), f"prompts/list entry {index} must be an object"
        name = prompt.get("name")
        if not isinstance(name, str) or not name:
            return (), f"prompts/list entry {index} must contain a non-empty string name"
        names.append(name)
    return tuple(names), None


def validate_resources_result(result: Any) -> tuple[tuple[str, ...], str | None]:
    if not isinstance(result, dict):
        return (), "resources/list result must be an object"
    raw_resources = result.get("resources")
    if not isinstance(raw_resources, list):
        return (), "resources/list result must contain a resources array"
    uris: list[str] = []
    for index, resource in enumerate(raw_resources):
        if not isinstance(resource, dict):
            return (), f"resources/list entry {index} must be an object"
        uri = resource.get("uri")
        if not isinstance(uri, str) or not uri:
            return (), f"resources/list entry {index} must contain a non-empty string uri"
        uris.append(uri)
    return tuple(uris), None


def _validate_object_schema(schema: Any, context: str) -> str | None:
    if not isinstance(schema, dict):
        return f"{context} must be an object"
    if schema.get("type") != "object":
        return f"{context} must declare type object"
    properties = schema.get("properties")
    if properties is not None and not isinstance(properties, dict):
        return f"{context} properties must be an object when present"
    required = schema.get("required")
    if required is not None and (
        not isinstance(required, list) or any(not isinstance(item, str) for item in required)
    ):
        return f"{context} required must be an array of strings when present"
    return None
