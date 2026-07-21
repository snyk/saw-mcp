# Snyk API & Web MCP Server — User Guide

## What it is

The Snyk API & Web MCP Server lets AI assistants (Cursor, Devin, Claude Code, etc.) interact with the Snyk API & Web security testing platform through natural language. You can manage targets, run scans, view findings, generate reports, and configure authentication — all via prompts.

> **Naming note:** Snyk API & Web was formerly known as Probely. The API endpoints (`api.probely.com`), web console (`plus.probely.app`), and MCP tool names (`probely_*`) still use the legacy domain and prefix. Environment variables and config sections use the new `SAW` / `saw` naming.

## Main value

**Agentic target onboarding.** The server is built so the AI can create and fully configure scan targets automatically. Instead of manually setting up targets in the Snyk UI, you describe what you want and the AI handles:

- **Authentication** — Login sequences (recorded via `playwright-cli` or Playwright MCP), form login fallback
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

> **Prerequisite for web targets:** The SAW MCP server does not include a browser. Login sequences are recorded via **`playwright-cli`** (preferred for coding agents with Shell) or **[Playwright MCP](https://playwright.dev/docs/getting-started-mcp)** (fallback for MCP-only clients). Without either, the AI cannot navigate the app and may produce an incorrect sequence format. See the [Cursor installation guide](docs/installation-guides/install-cursor.md#browser-automation-for-web-targets) for setup. If browser automation is unavailable, the AI falls back to form login for simple login pages.

> **More examples:** See **[prompts.md](prompts.md)** for a full catalog of prompts covering targets, scans, findings, credentials, reports, and multi-step workflows.

## Multiple targets

You can onboard several targets at once. For example:

*"Add these targets: app1.example.com (user1@example.com / pass1), app2.example.com (user2@example.com / pass2 / TOTP seed 34566424343)"*

The AI creates a **subagent per target**. With **`playwright-cli`**, subagents may run in parallel using distinct `-s=<session>` names. With **Playwright MCP**, subagents must run sequentially (one at a time) because Playwright MCP uses a single shared browser instance.

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

- **API key** — Prefer the `MCP_SAW_API_KEY` environment variable (or `.env`). Avoid storing a plaintext key in `config/config.yaml`, and do not put it in `~/.cursor/mcp.json`. If you must reference the key from config, use a secret reference — `op://vault/item/field` (resolved via the [1Password CLI](https://developer.1password.com/docs/cli/)) or `env:OTHER_VAR` — so the key never sits in plaintext. `MCP_SAW_API_KEY` also accepts these reference schemes. A plaintext key read from the config file logs a warning at startup.
- **Config file** — `config/config.yaml` is gitignored; keep it out of version control and use `chmod 600` on the file.
- **Target discovery** — On loading a project, the AI can match it to existing targets via `probely_list_targets`.
- **Findings** — Use the findings tools to prioritize fixes when vulnerabilities exist.

## Supported IDEs

- **Cursor** — Full support; install from the [Cursor Marketplace](https://cursor.com/marketplace/snyk/snyk-api-web) or follow [install-cursor.md](docs/installation-guides/install-cursor.md)
- **Devin** — Full support; install from Devin's MCP Marketplace by going to **Settings → Configuration → MCP servers → Open MCP Marketplace** and searching for **Snyk API & Web**
- **Any MCP-compatible IDE** — Standard protocol

## Links

- [Snyk API & Web API Reference](https://developers.probely.com/api/reference)
- [MCP Protocol](https://modelcontextprotocol.io)
