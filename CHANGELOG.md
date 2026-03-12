# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

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
