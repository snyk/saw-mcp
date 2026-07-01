---
name: saw-web-target-configuration
description: DEFAULT skill for creating Snyk API & Web targets. Use for all target creation requests unless the user explicitly mentions an API target, OpenAPI schema, Swagger spec, or Postman collection. Handles web application targets with authentication, login sequences, 2FA, and logout detection.
---

# Web Target Configuration Skill (Snyk API & Web)

Configure web application targets for Snyk API & Web security scanning with authentication support. For API targets, use the `saw-api-target-configuration` skill instead.

## Prerequisite: playwright-cli

Before running this skill, verify that `playwright-cli` is installed and Chromium is available:

```bash
playwright-cli --version
```

If the command is not found, run `./scripts/setup-playwright.sh` from the repo root. This installs `@playwright/cli` globally and downloads the Chromium binary.

## Target Type Check — Do This First

Before proceeding, determine whether this is an API target or a web target:

- If the user has provided an **OpenAPI/Swagger schema** (URL or file), a **Postman collection**, or explicitly said **"API target"** — stop and use the `saw-api-target-configuration` skill instead.
- Otherwise, **treat it as a web target by default**. If the user just says "add a target", "create a target", or provides a URL without further qualification, proceed here.

When you finish adding/configuring a target, always summarize it with a table, and include a link to the target on Snyk API & Web. Use the Snyk API & Web app URL **https://plus.probely.app**. Include a column if you added extra hosts or not and in case you did, which ones.

## Multiple Targets — MUST Use Subagents in Sequence

**When the user provides more than one target, you MUST launch subagents one at a time, waiting for each to finish before launching the next.** `playwright-cli` uses a single browser instance; parallel subagents would conflict.

Each subagent prompt should be short — just the target details and an instruction to read the skill file:

```
Configure a Snyk API & Web web target:
- URL: <url>
- Name: <name or "auto" — if "auto", derive from the site's <title>>
- Labels: <["Label1", ...] or "default" — if "default", do NOT pass labels param>
- Username: <user>
- Password: <pass>
- 2FA TOTP seed: <seed or "none">
- Browser session name: <domain> (use with `playwright-cli -s=<domain>` for ALL browser commands)

First, read the skill file at <ABSOLUTE_PATH_TO_THIS_SKILL_FILE> and follow the full workflow.
Return a summary with: target ID, name, URL, login sequence status, logout detection status, extra hosts, Snyk API & Web link (https://plus.probely.app/targets/{targetId}).
```

Launch **one** Task tool call at a time. Wait for it to complete before launching the next. After all finish, compile summaries into one table.

## Credentials Management — Recommended (Used by Default)

Use the credential manager for sensitive values (passwords, TOTP seeds, etc.) by default. Store values via `probely_create_credential` with `is_sensitive=True` and use the returned `uri` (e.g. `credentials://xxxx`) in the API. If the user explicitly declines, inline values are allowed.

### Shared Credentials Across Multiple Targets

When configuring multiple targets that use **the same credentials**, the credential may already exist in the credential manager from a previous target. Since sensitive (obfuscated) values cannot be read back, the agent cannot verify whether it matches — this causes a new credential entry per target, polluting the credential manager.

**Rule:** When multiple targets share the same credential and it already exists with `is_sensitive=True`, **prompt the user** to deobfuscate it (update to `is_sensitive=False` via `probely_update_credential`) so it can be read back and reused across targets. Inform the user why deobfuscation is needed.

**Workflow for shared credentials:**
1. Create the credential normally with `is_sensitive=True` for the first target.
2. When a subsequent target needs the same credential, find the existing one via `probely_list_credentials`.
3. If the existing credential is sensitive (`is_sensitive=True` or value is `null`), prompt the user: *"The credential '<name>' is obfuscated. To reuse it across multiple targets, it needs to be deobfuscated. Would you like to proceed?"*
4. If the user agrees, update it: `probely_update_credential(credentialId, is_sensitive=False)`.
5. Reuse the same credential `uri` for the new target.

### Browser Session Isolation

Browser automation uses `playwright-cli` via the Shell tool. Each subagent MUST use a **named session** (`-s=<domain>`) to get a fully isolated browser context (separate cookies, storage, network logs). This prevents cross-contamination when multiple targets are configured.

### Shell Timeout for Browser Commands

The Shell tool defaults to a 30-second timeout (`block_until_ms: 30000`), which is often too short for browser automation.

**ALWAYS set `block_until_ms: 60000` on Shell calls that run `playwright-cli`.** For slow targets/pages, use `block_until_ms: 90000`.

**Pattern:**
```
cred = probely_create_credential(
  name="<target_name> - <description>",
  value="the_actual_secret_value",
  is_sensitive=True
)
# cred["uri"] → "credentials://xxxx"
```

**Credential URIs:** Use the format `credentials://<credential_id>` (e.g., `credentials://4DY4qGohso1r`).
Get credential URIs from `probely_list_credentials` or `probely_create_credential`.
**Do NOT use template syntax like `{{cred-name}}`.**

## Web Application Onboarding Workflow

### Step 1: Gather Information and Determine Authentication Method

Ask the user for (or derive):
1. **Target URL**
2. **Target name** (User provided > site `<title>` > FQDN)
3. **Labels** (Only pass if specified by user, do not add "Agentic")
4. **Login credentials**
5. **2FA/MFA requirements**

**Authentication method:**
1. **Login Sequence** (preferred) — record the login in the browser using `playwright-cli`.
2. **Form Login** (fallback) — only when browser automation is unavailable.

#### Creating Duplicate Targets

To create a duplicate target (same URL as existing target), use `allow_duplicate=True`.

```python
probely_create_web_target(
  name="MyApp - Different Auth Method",
  url="https://app.example.com",
  allow_duplicate=True
)
```

#### Reachability Failures

If target creation fails because the target is unreachable or the domain cannot be resolved, ask the user whether you should retry with `skip_reachability_check=True`. Only retry after the user explicitly agrees.

### Step 2: Record the Login Sequence

Use `playwright-cli` via the Shell tool to navigate and record the login sequence.

1. **Open a browser session and navigate**: `playwright-cli -s=SESSION open <url>`
2. **Find the login page** — use `snapshot` and `goto`.
3. **Inspect form elements** — run `scripts/inspect-login-form.js` via `playwright-cli -s=SESSION eval '<js>'`.
4. **Fill credentials and submit** — use `snapshot`, `fill`, and `click`.
5. **Handle 2FA if needed** — use `probely_generate_totp`.
6. **Verify login success** — record `window.location.href`.
7. **Verify selectors are absent post-login** using `eval`.
8. **Detect external API hosts** — run `playwright-cli -s=SESSION network` at pre/post-login checkpoints.
9. **Generate sequence JSON** using `references/sequence-format.md`.
10. **Enable sequence login** — call `probely_configure_sequence_login(targetId, enabled=True)`.
11. **Close browser session** — `playwright-cli -s=SESSION close`

#### Configuration Tool Calls

```python
target = probely_create_web_target(name=..., url=..., desc=..., labels=...)
probely_create_sequence(targetId, name="Login Sequence", content="...", sequence_type="login", enabled=True, custom_field_mappings=[...])
probely_configure_sequence_login(targetId, enabled=True)
probely_configure_logout_detection(targetId, enabled=True, check_session_url=..., logout_detector_type=..., logout_detector_value=..., logout_condition=...)
probely_create_extra_host(targetId, hostname="...", ip_address="")
```

### Step 3: Using Form Login (Fallback)

Use this only when browser automation is unavailable.

```python
probely_configure_form_login(
  targetId,
  login_url="https://app.example.com/login",
  username_field="email",
  password_field="password",
  username="user@example.com",
  password="...",
  check_pattern="Welcome"
)
```
