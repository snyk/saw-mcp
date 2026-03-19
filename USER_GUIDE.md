# Snyk API & Web MCP Server — User Guide

## What it is

The Snyk API & Web MCP Server lets AI assistants (Cursor, Devin, Windsurf, Claude Code, etc.) interact with the Snyk API & Web security testing platform through natural language. You can manage targets, run scans, view findings, generate reports, and configure authentication — all via prompts.

> **Naming note:** Snyk API & Web was formerly known as Probely. The API endpoints (`api.probely.com`), web console (`plus.probely.app`), and MCP tool names (`probely_*`) still use the legacy domain and prefix. Environment variables and config sections use the new `SAW` / `saw` naming.

## Main value

**Agentic target onboarding.** The server is built so the AI can create and fully configure scan targets automatically. Instead of manually setting up targets in the Snyk UI, you describe what you want and the AI handles:

- **Authentication** — Login sequences (recorded via Playwright), form login
- **2FA** — TOTP configuration for multi-factor authentication
- **Logout detection** — Session checks and logout detectors
- **Extra hosts** — Automatic detection and configuration of API hosts

## Example: Add a target

**Prompt:** *"Add target taintedport.com using credentials jane@example.com / password123"*

The AI will:

1. Create the target in Snyk API & Web
2. Record a login sequence (navigates to the site, fills credentials, submits)
3. Configure logout detection (so the scanner knows when to re-authenticate)
4. Detect and add extra hosts (e.g. `api.taintedport.com` if the app calls it)

The target is ready for scanning.

> **More examples:** See **[prompts.md](prompts.md)** for a full catalog of prompts covering targets, scans, findings, credentials, reports, and multi-step workflows.

## Multiple targets

You can onboard several targets at once. For example:

*"Add these targets: app1.example.com (user1@example.com / pass1), app2.example.com (user2@example.com / pass2 / TOTP seed 34566424343)"*

The AI creates a **subagent per target** and configures them sequentially (one at a time), since Playwright uses a single browser instance that cannot be shared across parallel sessions.

## What's available

### Tool categories

| Category | Tools |
|----------|-------|
| Targets | Create, update, list, get, delete |
| Scans | Start, stop, list, get |
| Findings | List, get, update, bulk update |
| Authentication | Form login, sequence login, 2FA, logout detection |
| Sequences | Create, list, get, update |
| Credentials | List, get, create, update, delete |
| Extra hosts | Create, list, get, update |
| API targets | From OpenAPI, from Postman |
| Reports | Create, download |
| Other | Labels, teams, users, scanning agents, target settings |

**51 tools total**

### Key tools (selection)

- `probely_list_targets(search?)`, `probely_create_web_target(name, url, ...)`, `probely_start_scan(targetId, profile?)`
- `probely_list_findings(targetId, severity?, state?)`, `probely_update_finding(targetId, findingId, state)`
- `probely_create_sequence(...)`, `probely_configure_sequence_login(targetId, enabled)`
- `probely_create_credential(name, value, is_sensitive?)`, `probely_list_credentials(...)` — credentials are used by default for sensitive values (passwords, tokens, secrets) and linked to sequence custom fields for passwords
- `probely_configure_form_login(...)`, `probely_configure_2fa(...)`
- `probely_create_api_target_from_postman(...)`, `probely_create_api_target_from_openapi(...)`
- `probely_request(method, path, ...)` for any endpoint

## Tool filtering

You can enable or disable specific tools in `config/config.yaml`:

```yaml
# Whitelist (only these tools)
tools:
  enabled:
    - probely_list_targets
    - probely_create_web_target
    - probely_start_scan
    - probely_list_findings

# Blacklist (disable these)
tools:
  disabled:
    - probely_delete_target
    - probely_request
```

If `enabled` is set, it takes precedence. If neither is set, all tools are available.

## Confirmation prompts

All tools that create, update, or delete resources require explicit user confirmation before executing. When the AI calls one of these tools, a confirmation prompt appears in the IDE with a context-specific message (e.g. target name and URL) — the user must choose "Yes" or "No" before the action proceeds. The AI cannot bypass this.

This covers every write operation: creating targets/credentials/sequences, updating configurations, starting/stopping scans, managing findings, and deleting resources. Read-only operations (list, get) do not require confirmation.

## Security best practices

- **API key** — Store only in `config/config.yaml` (field `saw.api_key` or `probely.api_key`). Do not put it in `~/.cursor/mcp.json`.
- **Config file** — Keep `config/config.yaml` out of version control. Use `chmod 600` on the file.
- **Target discovery** — On loading a project, the AI can match it to existing targets via `probely_list_targets`.
- **Findings** — Use the findings tools to prioritize fixes when vulnerabilities exist.

## Supported IDEs

- **Cursor** — Full support with example config
- **Devin** — Full support
- **Windsurf** — Compatible
- **Any MCP-compatible IDE** — Standard protocol

## Links

- [Snyk API & Web API Reference](https://developers.probely.com/api/reference)
- [MCP Protocol](https://modelcontextprotocol.io)
