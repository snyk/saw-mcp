# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-03-19

### Fixed

- PATCH /target: corrected `targetId` vs `siteId` confusion causing incorrect target updates (#40).
- Credential lookup now uses credential `id` instead of `name` for accurate resolution (#40).
- Duplicate target creation no longer fails when a target already exists (#40).
- API authentication static headers and cookies now applied correctly (#40).

### Changed

- HTTP responses now logged at `DEBUG` level for improved traceability (#40).
- `saw-web` and `saw-api` SKILL.md files made uniform in structure and terminology (#40).

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
