from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, cast

from agent_plugin_diagnostics.clients.snippets import doctor_server_snippet
from agent_plugin_diagnostics.core.models import DiagnosticReport
from agent_plugin_diagnostics.core.rules import RULES
from agent_plugin_diagnostics.core.workflows import audit, probe, scan
from agent_plugin_diagnostics.reports.renderers import ReportFormat, render_report


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except BrokenPipeError:
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apd",
        description="Diagnose MCP and AI coding-agent plugin setups.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = _add_report_command(subparsers, "scan", "Discover MCP configs without checks.")
    scan_parser.set_defaults(func=_scan_command)

    audit_parser = _add_report_command(
        subparsers, "audit", "Discover configs and run static checks."
    )
    audit_parser.set_defaults(func=_audit_command)

    export_parser = _add_report_command(subparsers, "export", "Write an audit report.")
    export_parser.set_defaults(func=_audit_command)

    probe_parser = _add_report_command(
        subparsers, "probe", "Run static checks and controlled stdio probes."
    )
    probe_parser.add_argument("--server", help="Only probe a single server id.")
    probe_parser.set_defaults(func=_probe_command)

    explain_parser = subparsers.add_parser("explain", help="Explain a diagnostic rule.")
    explain_parser.add_argument("rule_id")
    explain_parser.set_defaults(func=_explain_command)

    init_parser = subparsers.add_parser("init", help="Print an MCP Doctor config snippet.")
    init_parser.add_argument(
        "--client", required=True, choices=["claude-code", "codex", "cursor", "vscode", "windsurf"]
    )
    init_parser.set_defaults(func=_init_command)

    serve_parser = subparsers.add_parser("serve-mcp", help="Run APD as an MCP server.")
    serve_parser.set_defaults(func=_serve_mcp_command)
    return parser


def _add_report_command(
    subparsers: argparse._SubParsersAction[Any],
    name: str,
    help_text: str,
) -> argparse.ArgumentParser:
    command = cast(argparse.ArgumentParser, subparsers.add_parser(name, help=help_text))
    command.add_argument("root", nargs="?", default=".", help="Workspace root to inspect.")
    command.add_argument("--home", default=None, help="Home directory override for tests or CI.")
    command.add_argument(
        "--format",
        default="terminal",
        choices=["terminal", "json", "markdown", "sarif"],
        help="Output format.",
    )
    command.add_argument("--output", default=None, help="Write output to a file instead of stdout.")
    return command


def _scan_command(args: argparse.Namespace) -> int:
    report = scan(root=Path(args.root), home=Path(args.home) if args.home else None)
    return _write_report(report, args.format, args.output)


def _audit_command(args: argparse.Namespace) -> int:
    report = audit(root=Path(args.root), home=Path(args.home) if args.home else None)
    _write_report(report, args.format, args.output)
    return (
        1
        if any(finding.severity.value in {"critical", "high"} for finding in report.findings)
        else 0
    )


def _probe_command(args: argparse.Namespace) -> int:
    report = probe(
        root=Path(args.root), home=Path(args.home) if args.home else None, server_id=args.server
    )
    _write_report(report, args.format, args.output)
    return (
        1
        if any(finding.severity.value in {"critical", "high"} for finding in report.findings)
        else 0
    )


def _write_report(report: DiagnosticReport, output_format: str, output: str | None) -> int:
    rendered = render_report(report, cast(ReportFormat, output_format))
    if output:
        Path(output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


def _explain_command(args: argparse.Namespace) -> int:
    rule = RULES.get(args.rule_id.upper())
    if not rule:
        sys.stderr.write(f"Unknown rule id: {args.rule_id}\n")
        return 2
    sys.stdout.write(
        "\n".join(
            [
                f"{rule.id}: {rule.title}",
                f"Severity: {rule.severity.value}",
                f"Category: {rule.category}",
                "",
                rule.description,
                "",
                f"Fix: {rule.suggestion}",
            ]
        )
        + "\n"
    )
    return 0


def _init_command(args: argparse.Namespace) -> int:
    sys.stdout.write(doctor_server_snippet(str(args.client)))
    return 0


def _serve_mcp_command(_: argparse.Namespace) -> int:
    from agent_plugin_diagnostics.mcp_server.server import run

    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
