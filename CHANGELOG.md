# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.2.0] - 2026-07-20

### Security

- **Destructive tools disabled by default (DAST-1174)**: `probelyrequest` (the raw "call any API" passthrough), `probely_delete_target`, `probely_delete_credential`, and `probely_bulk_update_findings` are now blocked out of the box via a built-in `DEFAULT_DISABLED_TOOLS` list that applies even in env-only mode (no config file). Using one requires explicitly opting in through the `tools.enabled` whitelist. This also fixes the safe-default config, which previously blocked the non-existent name `probely_request` instead of the real tool name `probelyrequest`, leaving the raw passthrough enabled.
- **Per-tool-call audit trail (DAST-1174)**: every MCP tool invocation now emits one structured audit line (tool name, UTC timestamp, outcome — `success` / `api_error` / `error` — and duration). Lines go to the standard log by default; set `MCP_SAW_AUDIT_LOG` to also append them to a dedicated, SIEM-ingestible file.
- **Secrets management for the API key**: the API key may now be provided as a secret reference instead of a plaintext value, so it never has to sit in `config/config.yaml`. `MCP_SAW_API_KEY` and the config `api_key` field accept `op://vault/item/field` (resolved at runtime via the 1Password CLI) and `env:OTHER_VAR` (indirection to another environment variable). A plaintext key read from the config file now logs a warning recommending the env var / secret reference, and `config/config.yaml.dist`, `.env.example`, and the user guide document `MCP_SAW_API_KEY` as the supported path (`config/config.yaml` is already gitignored).
- **SSRF protection for API-target schema fetches**: `_fetchjson_or_url` (used by `probely_create_api_target_from_postman` / `probely_create_api_target_from_openapi`) now validates user-supplied URLs before fetching. Only `https://` is permitted, hostnames are resolved and any address in a private, loopback, link-local, reserved, multicast, or unspecified range is rejected (blocking cloud-metadata endpoints like `169.254.169.254` and `localhost`), redirects are re-validated on every hop, and an optional host allow-list can be configured via the `MCP_SAW_URL_ALLOWLIST` environment variable.

### Added

- **Dual-path browser automation for web targets**: `playwright-cli` (preferred for coding agents with Shell) with Playwright MCP as fallback. New `./scripts/setup-playwright.sh` installs `@playwright/cli` and Chromium. CI smoke test verifies install and basic browser session. Updated skill, rules, install guides, and docs.
- **Cursor Marketplace install**: restored documentation for one-click installation from the [Cursor Marketplace](https://cursor.com/marketplace/snyk/snyk-api-web) now that the plugin is published.
- **Devin MCP Marketplace install**: updated documentation for the current Devin product and marketplace flow, replacing the old product references.

### Changed

- **Web target configuration skill**: dual-path workflow (`playwright-cli` first, Playwright MCP fallback, form login last). Broader extra-host detection includes cross-domain application hosts.

### Fixed

- **Version coherence**: `.cursor-plugin/plugin.json` version synced to `1.2.0` to match `pyproject.toml`, `server.json`, and `snyk_apiweb/__init__.py`.
- **`.env.example`**: documents optional `MCP_SAW_CONFIG_PATH` and `MCP_SAW_LOG_LEVEL` env vars.

## [1.1.3] - 2026-05-13

### Added

- **Devin MCP Marketplace install**: the MCP server is listed in Devin's MCP Marketplace and can be installed from **Settings → Configuration → MCP servers → Open MCP Marketplace**. Updated `install-devin.md` to document this as the recommended install path, and updated `README.md` quick-start accordingly.

### Fixed

- `snyk_apiweb/__init__.py` version was not updated in the 1.1.1 and 1.1.2 releases; corrected to `1.1.3`.

## [1.1.0] - 2026-03-24

### Added

- **Cursor Marketplace plugin**: `.cursor-plugin/plugin.json` manifest and `.mcp.json` for one-click installation from the Cursor Marketplace.
- **`uvx` one-command install**: run the server directly from GitHub without cloning — `uvx --from git+https://github.com/snyk/saw-mcp.git saw-mcp`.
- **`saw-mcp` console script entry point**: `pyproject.toml` now declares a `[project.scripts]` entry, enabling `uvx` and `pipx` execution.

### Changed

- All installation guides (Cursor, Claude Desktop, Devin, VS Code) updated with `uvx` as the primary install option alongside the existing local clone method.
- Cursor install guide restructured with Marketplace as the recommended path and manual options (uvx, local clone) as alternatives.
- Removed non-public environment URLs from documentation.

## [1.0.0] - 2026-03-20

First stable release of the Snyk API & Web MCP Server. This version marks the tool as
production-ready for connecting AI coding assistants to Snyk API & Web to onboard DAST
scan targets, configure authentication, and triage findings — all through natural language.
Works with Cursor, Claude Code, Devin, and any MCP-compatible client.

### Added

- **Web target configuration** via the `saw-web-target-configuration` skill: record and replay multi-step login sequences — including TOTP/2FA — to configure authenticated DAST scanning targets.
- **API target configuration**: onboard API scan targets directly from OpenAPI schemas, Swagger documents, and Postman collections.
- **Credential management**: securely store and reuse credentials across targets via `probely_create_credential`; sensitive values are kept as credential URIs and never exposed in plain text.
- **Login sequence management**: create, update, and enable login sequences with support for standard forms, multi-step flows, and TOTP-based 2FA via `probely_create_sequence` and `probely_configure_sequence_login`.
- **Confirmation guardrail for destructive operations**: explicit user confirmation required before any action that modifies or deletes existing scan configuration.
- **Elicitation support**: interactive guided forms for collecting target configuration, with automatic fallback for CLI-based MCP clients that do not support forms.
- **Configurable log verbosity**: control server output via `MCP_SAW_LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`; default: `INFO`).
- **Optional credentials manager**: server starts and operates fully even when the credentials manager is not configured.
- **Example prompts catalog** (`prompts.md`): ready-to-use prompt library covering single-target onboarding, bulk workflows, credential reuse, and scan triage.
- **Installation guides** for Cursor, Claude Desktop, Devin, and VS Code.
- **Secure API key setup** via `scripts/setup-env.sh` — stores the key in a gitignored `.env` file without exposing it in shell history.

### Fixed

- PATCH /target: corrected `targetId` vs `siteId` confusion causing incorrect target updates (#40).
- Credential lookup now uses credential `id` instead of `name` for accurate resolution (#40).
- Duplicate target creation no longer fails when a target already exists (#40).
- API authentication static headers and cookies now applied correctly (#40).

### Changed

- HTTP responses logged at `DEBUG` level for easier troubleshooting (#40).
- `saw-web` and `saw-api` skill files unified in structure and terminology for consistency (#40).
- README restructured to present tarball download and git clone as explicit alternatives (Option A / Option B) (#48).
- Standalone server mode documented as a development and debugging tool — not required for normal MCP client usage (#48).
- `saw-web-target-configuration` skill is now the **default** for all target creation requests; `saw-api-target-configuration` is only selected when the user explicitly provides an OpenAPI/Swagger schema, Postman collection, or says "API target". Eliminates ambiguous skill selection on weaker models.
- Web and API target onboarding guidance now instructs the agent to offer a retry with `skip_reachability_check=True` when initial target creation fails because the domain is unreachable or cannot be resolved.

## [0.9.4] - 2026-03-19

### Changed

- Credential management is now the default behaviour: passwords are stored via `probely_create_credential` and linked in `custom_field_mappings` unless the user explicitly declines (#36).
- Login sequence and update-sequence tools now use credential URIs for sensitive values by default (#36).
- When multiple targets share a credential that is already marked `is_sensitive=True`, the user is prompted to deobfuscate it to allow reuse (#36).
- Username `value_is_sensitive` flag set to `true` in login sequences (#36).
- Global documentation refresh across README, USER_GUIDE, AppBuilder, prompts, skills, and installation guides (#39).
- `.env.example` and `config.yaml.dist` updated to reflect current configuration options (#39).

## [0.9.3] - 2026-03-17

### Added

- `log_level` environment variable to control server logging verbosity (#23).
- Tool name included in `DEBUG`-level log messages for easier tracing (#27).
- VS Code installation guide in documentation (#22).
- Credentials manager is now optional; server starts without it when not configured.

### Fixed

- Create API targets tool — multiple issues causing incorrect target creation (#24).
- Auto-approve flow bypassing elicitation for unsupported clients (FAW-606).
- Credentials manager capabilities being applied by default unintentionally (FAW-606).
- Login sequence now correctly re-enables after being configured.
- Skills base directory resolution.
- CLA check no longer blocks the CI pipeline (#28).

### Changed

- `saw-web-target-configuration` skill refactored for progressive disclosure (#26).
- Removed user elicitation confirmation step from the create-target tool.
- All internal references renamed from `saw-mcp-server` to `saw-mcp` (#20).
- CircleCI restructured into a single CICD workflow with `snyk/prodsec-orb` (#31, #32).
- CI action upgrades: `actions/checkout` to v6 (#17, #29), `actions/setup-python` to v6 (#18, #30), `actions/upload-artifact` to v7 (#19).
- Repository brought into compliance with Snyk open-source repo standards (#25).

## [0.9.2] - 2025-06-01

### Added

- Confirmation decorator (`register_tool_with_confirmation`) for destructive operations.
- Credentials manager support for custom headers, cookies, basic auth, and TOTP seed.
- Example prompts catalog (`prompts.md`) with cross-references from README and USER_GUIDE.
- Elicitation fallback for CLI clients that do not support forms.

### Fixed

- `check_client_capability` guard for Claude Code method-not-found errors.
- Confirmation handling scoped to CLI transport level.

### Changed

- Ruff lint and format applied across codebase.
- Banner updated to `Snyk_API_and_Web_Banner.webp`.
