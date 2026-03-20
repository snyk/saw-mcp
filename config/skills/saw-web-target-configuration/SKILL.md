---
name: saw-web-target-configuration
description: Configure Snyk API & Web web application targets with authentication, login sequences, 2FA, and logout detection. Use when creating web app targets with form-based or sequence-based authentication.
---

# Web Target Configuration Skill (Snyk API & Web)

Configure web application targets for Snyk API & Web security scanning with authentication support. For API targets, use the `saw-api-target-configuration` skill instead.

## Prerequisite: playwright-cli

Before running this skill, verify that `playwright-cli` is installed and Chromium is available:

```bash
playwright-cli --version
```

If the command is not found, run `./scripts/setup-playwright.sh` from the repo root. This installs `@playwright/cli` globally and downloads the Chromium binary.

When you finish adding/configuring a target, always summarize it with a table, and include a link to the target on SAW. Use the SAW app URL **https://plus.probely.app**. Include a column if you added extra hosts or not and in case you did, which ones.

## Multiple Targets — MUST Use Subagents in Parallel

**When the user provides more than one target, you MUST launch ALL subagents in a single message.**

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

Launch **all** Task tool calls in a **single assistant message** (max 10 at a time). Do NOT wait for one to finish before launching the next. After all finish, compile summaries into one table.

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

Browser automation uses `playwright-cli` via the Shell tool. Each subagent MUST use a **named session** (`-s=<domain>`) to get a fully isolated browser context (separate cookies, storage, network logs). This prevents cross-contamination when multiple targets are configured in parallel.

### Shell Timeout for Browser Commands

The Shell tool defaults to a 30-second timeout (`block_until_ms: 30000`), which is **too short** for browser automation. `playwright-cli` commands launch a Chromium instance, navigate to pages, and wait for content to load — this routinely exceeds 30 seconds, especially under parallel load.

**ALWAYS set `block_until_ms: 60000` (60 seconds) on every Shell call that runs a `playwright-cli` command.** For particularly slow targets or heavy pages, use `block_until_ms: 90000`.

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

**Pattern:**
```
cred = probely_create_credential(
  name="<target_name> - <description>",
  value="the_actual_secret_value",
  is_sensitive=True                       # always sensitive by default
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

**Authentication method:** Always configure authentication using a **login sequence** recorded via `playwright-cli`.

#### Creating Duplicate Targets

To create a duplicate target (same URL as existing target), use `allow_duplicate=True`. This is useful when you want multiple targets for the same URL with different configurations (e.g., different authentication methods, different test scenarios):

```python
probely_create_web_target(
  name="MyApp - Different Auth Method",
  url="https://app.example.com",  # Same URL as existing target
  allow_duplicate=True  # Bypass duplicate URL check
)
```

### Step 2: Record the Login Sequence

Use `playwright-cli` via the Shell tool to navigate and record the login sequence. Use the session name provided in the subagent prompt (or derive from the target domain for single-target flows).

1. **Open a browser session and navigate**: `playwright-cli -s=SESSION open <url>`
2. **Find the login page** — use `snapshot` to see the page and `goto <url>` to navigate. Record the login page URL.
3. **Inspect the current step's form elements** — run `scripts/inspect-login-form.js` via `playwright-cli -s=SESSION eval '<js>'` to detect what's visible. Run this on every step of the login flow.
4. **Fill credentials and submit** — use `snapshot` to get element refs, then `fill <ref> '<value>'` and `click <ref>`. Record CSS selectors for the login sequence JSON.
5. **Handle 2FA if needed** — use `probely_generate_totp` to get a code for the live login.
6. **Verify login success** — record the absolute URL via `playwright-cli -s=SESSION eval '() => window.location.href'` for logout detection.
7. **Verify login selectors are NOT on the post-login page** — test if login selectors still exist using `eval`.
8. **Detect external API hosts (CRITICAL)** — run `playwright-cli -s=SESSION network` at checkpoint 1 (after login page loads) and checkpoint 2 (after login). Read `references/extra-hosts.md` for full instructions.
9. **Generate the login sequence JSON** — Read `references/sequence-format.md` for the correct JSON format using custom fields.
10. **Enable authentication with login sequence** — call `probely_configure_sequence_login(targetId, enabled=True)`.
11. **Close the browser session** — `playwright-cli -s=SESSION close`

#### Configuration Tool Calls

```python
target = probely_create_web_target(name=..., url=..., desc=..., labels=...) # Use target["id"] as targetId

# Build the sequence JSON and pass it to probely_create_sequence
probely_create_sequence(targetId, name="Login Sequence", content="...", sequence_type="login", enabled=True, custom_field_mappings=[...])

# Enable sequence login
probely_configure_sequence_login(targetId, enabled=True)

# Configure logout detection. See references/logout-detection.md
probely_configure_logout_detection(targetId, enabled=True, check_session_url=..., logout_detector_type=..., logout_detector_value=..., logout_condition=...)

# Add extra hosts if detected. See references/extra-hosts.md
probely_create_extra_host(targetId, hostname="...", ip_address="")
```
