# Rule Index

| Rule | Severity | Category | Title |
| --- | --- | --- | --- |
| APD001 | high | configuration | Invalid configuration file |
| APD002 | low | configuration | No server definitions found |
| APD010 | high | configuration | Server has no launcher |
| APD011 | high | runtime | Command is not available |
| APD012 | medium | runtime | Working directory is missing |
| APD013 | medium | runtime | Referenced argument path is missing |
| APD020 | medium | environment | Required environment variable is missing |
| APD021 | high | security | Literal secret in configuration |
| APD030 | medium | supply-chain | Package invocation is not pinned |
| APD031 | medium | transport | Remote server uses plain HTTP |
| APD040 | low | portability | Interpolation syntax may not work in this client |
| APD050 | low | portability | Project config contains an absolute local path |
| APD060 | high | security | Filesystem server root is too broad |
| APD070 | low | usability | Server name collision |
| APD080 | medium | probe | Probe failed |
| APD081 | medium | protocol | Protocol compliance failed |

Use `apd explain <rule-id>` for the detailed explanation and suggested fix. Probe failures now cover stdio, Streamable HTTP, and SSE probe attempts, including initialize, initialized notification, ping, tools/list, and advertised prompt/resource discovery. APD081 is reserved for responses that are reachable but non-compliant with the JSON-RPC or MCP result shape APD exercised.
