# AGENTS.md

Guidance for AI coding agents (Cursor, Claude Code, Copilot, etc.) working in this repo.

## What this is

`saw-mcp` is the **Snyk API & Web MCP server** — a FastMCP 2.0 Python package that exposes
`probely_*` tools so AI assistants can onboard DAST targets, configure authentication, run
scans, and triage findings. It is distributed via PyPI (`snyk-apiweb-mcp`), the Cursor
Marketplace (`.cursor-plugin/`), and the MCP registry (`server.json`).

**Naming:** Snyk API & Web was formerly Probely. The platform API (`api.probely.com`), console
(`plus.probely.app`), and MCP tool names (`probely_*`) still use the legacy prefix. Config and
env vars use `SAW` / `saw` / `MCP_SAW_*`.

Owner: `@snyk/emerging-technologies-solutions_probely` (see `.github/CODEOWNERS`).

## Repo layout

```
snyk_apiweb/           Python package — server entry point and all MCP tools
  server.py            `main()` / `saw-mcp` console script
  tools.py             FastMCP tool definitions (`probely_*`)
  probely_client.py    HTTP client for api.probely.com (mocked in tests)
  config.py            YAML + env config loading, tool allow/deny lists
  audit.py             Tool-call audit logging
config/
  config.yaml.dist     Committed template — copy to config/config.yaml locally
  saw_rules.mdc        Cursor plugin rules (shipped via .cursor-plugin/)
  skills/              Agent skills for web/API target onboarding workflows
tests/                 pytest suite (network calls mocked — no live API key needed)
scripts/
  dev.sh               FastMCP hot-reload dev server
  package.sh           Build release tarball under dist/
  setup-env.sh         Interactive .env writer (API key)
  setup-playwright.sh  Install playwright-cli + Chromium for web-target smoke tests
docs/installation-guides/   Per-IDE setup docs
.cursor-plugin/        Cursor Marketplace manifest (version must match package)
server.json            MCP registry metadata (version must match package)
```

User-facing docs: `README.md` (install), `USER_GUIDE.md` (tools), `prompts.md` (example prompts).

## Setup

Prerequisites: **Python 3.10+** (CI tests 3.10–3.12). Node 18+ only if you work on web-target
skills or run the playwright-cli smoke test.

```bash
python -m venv venv
source venv/bin/activate
pip install setuptools wheel && pip install -e ".[dev]"
```

Optional local config (not required when `MCP_SAW_API_KEY` is set):

```bash
cp config/config.yaml.dist config/config.yaml
./scripts/setup-env.sh   # writes gitignored .env with API key
```

Never commit `.env`, `config/config.yaml`, or plaintext API keys.

## Commands

Use these exact commands — don't invent alternatives.

| Task | Command |
| --- | --- |
| Install (editable + dev) | `pip install setuptools wheel && pip install -e ".[dev]"` |
| Run tests | `pytest tests/ -v` |
| Lint | `ruff check .` |
| Format check | `ruff format --check .` |
| Auto-format | `ruff format .` |
| Dev server (hot reload) | `./scripts/dev.sh` (requires `venv` and `fastmcp` dev extras) |
| Standalone server | `python -m snyk_apiweb.server` |
| Release tarball | `bash scripts/package.sh` → `dist/SnykAPIWeb-<version>.tgz` |
| Playwright smoke test | `./scripts/setup-playwright.sh && ./scripts/smoke-test-playwright.sh` |

For a quick inner loop: `pytest tests/ -v` and `ruff check .`. Run the full CI matrix locally
when changing Python compatibility.

## Testing rules

- Tests live under `tests/` and use **mocked HTTP** (`tests/conftest.py` provides a `client`
  fixture with a patched `requests.Session`). No live `MCP_SAW_API_KEY` is needed for unit tests.
- Use `tmp_config` fixture to write temporary YAML config files.
- Do not add integration tests that hit `api.probely.com` without explicit team approval and
  CI secrets wiring.
- Web-target browser automation is covered by `scripts/smoke-test-playwright.sh` in CI, not
  by pytest.

## CI

- **GitHub Actions** (`.github/workflows/ci.yml`): pytest on Python 3.10/3.11/3.12, ruff
  lint + format, playwright-cli smoke test.
- **CircleCI** (`.circleci/config.yml`): pytest, ruff, prodsec security scans.
- **Release** (`.github/workflows/release.yml`): triggered by `v*` tags; tag must match
  `pyproject.toml` / `snyk_apiweb/__init__.py` / `server.json` / `.cursor-plugin/plugin.json`.

## Version bumps and releases

Version is declared in **four places** — keep them in sync:

1. `snyk_apiweb/__init__.py` (`__version__`)
2. `pyproject.toml` (`project.version`)
3. `server.json` (`version` and `packages[0].version`)
4. `.cursor-plugin/plugin.json` (`version`)

Release flow: bump all four → merge → tag `vX.Y.Z` → CI builds wheel/sdist/tarball and publishes
to PyPI. Update `CHANGELOG.md` for user-visible changes.

## MCP / plugin changes

When adding or changing tools:

- Implement in `snyk_apiweb/tools.py`; HTTP plumbing in `probely_client.py`.
- Update `USER_GUIDE.md` and/or `prompts.md` when behavior is user-visible.
- Update skills under `config/skills/` when onboarding workflows change.
- Fill in the **MCP Impact** section of the PR template.
- Destructive tools (`probely_delete_*`, `probelyrequest`, `probely_bulk_update_findings`) are
  **disabled by default** in `config.py` (`DEFAULT_DISABLED_TOOLS`). Do not enable them globally
  without an explicit opt-in story.

`config/saw_rules.mdc` is the canonical behavioral rules file for the Cursor plugin — keep it
aligned with tool usage constraints (always use MCP tools, never call the REST API directly).

## Security and secrets

This repo handles **DCL4–DCL6** data (API keys, login credentials, scan findings). See
`SECURITY.md` for classification and logging/redaction rules.

- API key: `MCP_SAW_API_KEY` env var (preferred) or gitignored `config/config.yaml`.
- Server logs to `~/saw-mcp.log` — never log secrets; `probely_client.py` redacts sensitive keys
  at DEBUG level.
- `scripts/package.sh` redacts `api_key` in staged tarballs as `CHANGEME`.

Do not commit secrets, customer credentials, or real scan findings in tests or fixtures.

## Generated / gitignored artifacts — do not commit

| Path | Notes |
| --- | --- |
| `venv/`, `__pycache__/`, `*.egg-info/` | Local Python env |
| `dist/`, `*.tgz` | Build output from `package.sh` / release |
| `.env`, `config/config.yaml` | Local secrets and overrides |
| `.ruff_cache/`, `.pytest_cache/` | Tool caches |
| `.playwright-cli/` | Browser automation session state |
| `node_modules/`, `package.json`, `package-lock.json` | Ephemeral Node deps for skill scripts |
| `.cursor/rules/snyk_rules.mdc` | Auto-generated by Snyk IDE extension |

## Things not to touch without good reason

- `uv.lock` — only update deliberately when adopting uv-based workflows (CI uses pip).
- `config/config.yaml.dist` — template for end users; avoid embedding real keys or instance URLs.
- Test fixtures — keep tests hermetic; don't add network-dependent fixtures.
- Legacy env names (`MCP_PROBELY_*`) — still supported for backward compatibility; don't remove
  without a deprecation plan.

## Commit and PR conventions

- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
- Use the PR template (`.github/pull_request_template.md`); call out MCP tool changes explicitly.
- Ruff: line length 79, target Python 3.10 (`pyproject.toml`).

## When in doubt

- Tool behavior and schemas: start at `snyk_apiweb/tools.py`.
- Config precedence and tool filtering: `snyk_apiweb/config.py`.
- HTTP client and redaction: `snyk_apiweb/probely_client.py`.
- End-user documentation: `USER_GUIDE.md`, `prompts.md`, `docs/installation-guides/`.
