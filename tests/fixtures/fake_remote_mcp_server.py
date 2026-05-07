from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP


def main() -> None:
    port = int(sys.argv[1])
    transport = sys.argv[2]
    mcp = FastMCP(
        "fake-remote",
        host="127.0.0.1",
        port=port,
        stateless_http=True,
        json_response=True,
    )

    @mcp.tool()
    def ping_tool() -> str:
        return "pong"

    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
