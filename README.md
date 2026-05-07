# MCP Doctor

MCP Doctor is a Python-first diagnostic toolkit for MCP and AI coding-agent plugin setups. It helps developers inspect, audit, and debug MCP configuration across clients such as Claude Code, Codex, Cursor, VS Code, and Windsurf.

The project is designed to be useful from the first install:

- Discover local MCP configuration across supported clients.
- Normalize server definitions into one reportable model.
- Detect broken commands, missing environment variables, risky config, and portability issues.
- Probe MCP servers safely enough to confirm startup and tool discovery.
- Export reports for terminals, issue comments, CI, and agent workflows.
- Run as an MCP server so agents can diagnose their own tool setup.

This repository is starting with the product plan and implementation foundation. The first working release will focus on local-first diagnostics, clear reports, and a contributor-friendly Python architecture.

## Status

Early implementation. The initial feature branch will add the Python package, CLI, tests, documentation, and MCP server mode.
