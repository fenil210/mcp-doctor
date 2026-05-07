from __future__ import annotations

import json
import sys


def write(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    if method == "initialize":
        write(
            {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "fake", "version": "0.1.0"},
                },
            }
        )
    elif method == "ping":
        write({"jsonrpc": "2.0", "id": request["id"], "result": {}})
    elif method == "tools/list":
        write(
            {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"tools": [{"name": "ping", "inputSchema": {"type": "object"}}]},
            }
        )
