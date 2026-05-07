from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
ENV_REF_RE = re.compile(
    r"\$\{env:([A-Za-z_][A-Za-z0-9_]*)\}|\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-[^}]*)?\}|\$([A-Za-z_][A-Za-z0-9_]*)"
)
PLACEHOLDER_RE = re.compile(r"^<[^>]+>$|^\$\{[^}]+}$|^\$[A-Za-z_][A-Za-z0-9_]*$")
SECRET_KEY_RE = re.compile(r"(api[_-]?key|token|secret|password|pat|bearer|authorization)", re.I)
SECRET_VALUE_RE = re.compile(
    r"^(sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|xox[baprs]-[A-Za-z0-9-]{12,}|eyJ[A-Za-z0-9_-]{20,})"
)


def expand_user_path(value: str, home: Path | None = None) -> Path:
    if value.startswith("~"):
        base = home or Path.home()
        return base / value[2:] if value.startswith("~/") or value.startswith("~\\") else base
    return Path(value)


def is_absolute_path(value: str) -> bool:
    return Path(value).is_absolute() or bool(WINDOWS_ABSOLUTE_RE.match(value))


def has_unexpanded_placeholder(value: str) -> bool:
    return "${" in value or "$" in value


def referenced_env_vars(value: str) -> set[str]:
    names: set[str] = set()
    for match in ENV_REF_RE.finditer(value):
        for group in match.groups():
            if group:
                names.add(group)
    return names


def is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER_RE.match(value.strip()))


def looks_like_secret(key: str, value: str) -> bool:
    if not value or is_placeholder(value):
        return False
    if SECRET_VALUE_RE.search(value.strip()):
        return True
    return bool(SECRET_KEY_RE.search(key)) and len(value.strip()) >= 12


def command_exists(command: str, home: Path | None = None) -> bool:
    if has_unexpanded_placeholder(command):
        return True
    candidate = expand_user_path(command, home)
    if is_absolute_path(command) or "/" in command or "\\" in command:
        return candidate.exists()
    return shutil.which(command) is not None


def is_probably_path(value: str) -> bool:
    if not value or value.startswith("-") or has_unexpanded_placeholder(value):
        return False
    if value.startswith(("http://", "https://")):
        return False
    return (
        value.startswith((".", "~", "/", "\\"))
        or bool(WINDOWS_ABSOLUTE_RE.match(value))
        or "/" in value
        or "\\" in value
    )


def is_loopback_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"} or host.startswith("127.")


def merged_env(server_env: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {key: value for key, value in server_env.items() if not has_unexpanded_placeholder(value)}
    )
    return env


def redact_value(key: str, value: str) -> str:
    if looks_like_secret(key, value):
        return "<redacted>"
    return value
