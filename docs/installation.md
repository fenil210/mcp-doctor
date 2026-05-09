# Installation

The published package name is `agent-plugin-diagnostics`.

The installed commands are:

- `apd`
- `mcp-doctor`

## Recommended

Use `pipx` when you want APD installed as a normal command-line app in an isolated Python environment:

```bash
pipx install agent-plugin-diagnostics
apd --help
```

Upgrade later with:

```bash
pipx upgrade agent-plugin-diagnostics
```

## Fast Install With uv

Use `uv tool install` if you prefer uv-managed command-line tools:

```bash
uv tool install agent-plugin-diagnostics
apd --help
```

Run APD once without installing it permanently:

```bash
uvx --from agent-plugin-diagnostics apd audit
```

## Virtual Environment

Use `pip` inside a project or tool virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install agent-plugin-diagnostics
apd --help
```

On macOS and Linux, activate with:

```bash
source .venv/bin/activate
```

## Local Development

Clone the repository when you want to contribute:

```bash
git clone https://github.com/fenil210/mcp-doctor.git
cd mcp-doctor
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m pytest
```

On macOS and Linux, activate with `source .venv/bin/activate`.

## Source Install Fallback

Use a Git URL only when testing unreleased changes:

```bash
pipx install "agent-plugin-diagnostics @ git+https://github.com/fenil210/mcp-doctor.git"
```

For normal users, prefer the PyPI commands above.
