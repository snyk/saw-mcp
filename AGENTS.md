# AGENTS.md

## Cursor Cloud specific instructions

This repo is the **Snyk API & Web MCP Server** (`snyk-apiweb-mcp`, package `snyk_apiweb`) — a single Python 3.10+ FastMCP server that speaks the **stdio** transport (no HTTP port, no database). All `probely_*` tools proxy the external Snyk API & Web SaaS API at `https://api.probely.com`; only network-free tools (e.g. `probely_generate_totp`) work without a valid key.

### Environment
- A virtualenv is created at `./venv` and dev dependencies are installed via `pip install -e ".[dev]"` (the startup update script handles this). Activate with `source venv/bin/activate` or call binaries directly as `./venv/bin/<tool>`.
- `config.py` imports `python-dotenv`; it is currently pulled in transitively (via `pydantic-settings`) but the update script also installs `requirements.txt` to guarantee it.

### Lint / test / run (see also `.github/workflows/ci.yml`)
- Lint: `./venv/bin/ruff check .` and `./venv/bin/ruff format --check .`
- Test: `./venv/bin/pytest tests/ -v` — the suite is fully mocked, so **no API key or network is required**.
- Run the server (stdio, blocks waiting for an MCP client): `./venv/bin/python -m snyk_apiweb.server`. `scripts/dev.sh` runs `fastmcp dev` for hot reload.

### Non-obvious gotchas
- `build_server()` calls `get_probely_api_key()` at startup and **raises `RuntimeError` if no key is set**. To start/smoke-test the server without real credentials, set a dummy `MCP_SAW_API_KEY` (≥20 chars), e.g. `MCP_SAW_API_KEY=local-dev-dummy-key-not-a-real-key-000000`. Tools that hit `api.probely.com` will then fail auth, but the server boots and offline tools work.
- To exercise the server end-to-end without an IDE, drive it over stdio with the `mcp` client library (installed with the dev deps): initialize, `list_tools` (currently 51 tools + 2 prompts), and call `probely_generate_totp` (a network-free tool).
- Real end-to-end scanning requires `MCP_SAW_API_KEY` (from `https://plus.probely.app/api-keys`) and network access to `api.probely.com`; store it via env var or `./scripts/setup-env.sh` (writes gitignored `.env`).
- Playwright/Chromium (`./scripts/setup-playwright.sh`) is **optional** — only needed for the web-target login-recording skill.
- FastMCP performs a version check against `pypi.org` on startup; harmless if egress is blocked.
