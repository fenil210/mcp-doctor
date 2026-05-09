# Releasing

APD is prepared for PyPI releases through GitHub Actions and PyPI Trusted Publishing.

## One-Time PyPI Setup

Create or claim the PyPI project named `agent-plugin-diagnostics`.

Configure a PyPI trusted publisher:

- Owner: `fenil210`
- Repository: `mcp-doctor`
- Workflow name: `publish.yml`
- Environment name: `pypi`

Create a GitHub environment named `pypi`. Add a required reviewer if you want a manual approval gate before publishing.

## Release Flow

1. Update `version` in `pyproject.toml`.
2. Update `__version__` in `src/agent_plugin_diagnostics/__init__.py`.
3. Open and merge the version bump PR.
4. Create a GitHub release tagged as `v<version>`, for example `v0.1.0`.
5. The publish workflow builds the wheel and source distribution, verifies the package metadata, smoke-installs the wheel, then publishes to PyPI with trusted publishing.

## Local Package Check

Before tagging, you can build and inspect the package locally:

```bash
python -m pip install -e ".[dev]"
python -m build
python -m twine check dist/*
python -m pip install --force-reinstall dist/*.whl
apd --help
```

Delete `dist/` before rebuilding if you want a clean local artifact set.
