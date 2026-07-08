---
name: saw-web-target-configuration
description: DEFAULT skill for creating Snyk API & Web targets. Use for all target creation requests unless the user explicitly mentions an API target, OpenAPI schema, Swagger spec, or Postman collection. Handles web application targets with login sequences, 2FA, logout detection, and extra hosts via playwright-cli (preferred) or Playwright MCP (fallback).
---

# Web Target Configuration Skill (Snyk API & Web)

Configure web application targets for Snyk API & Web security scanning with authentication support. For API targets, use the `saw-api-target-configuration` skill instead.

## Browser Automation — Detect Before Recording

Login sequences require a real browser. **Detect availability in this order:**

### 1. `playwright-cli` (preferred for coding agents with Shell access)

```bash
playwright-cli --version
# or: npx @playwright/cli --version
```

If missing, install (no repo clone required):

```bash
npm install -g @playwright/cli@latest
playwright-cli install-browser chromium
```

Or, when a clone of this repo is available:

```bash
./scripts/setup-playwright.sh
```

Use **`npx @playwright/cli`** instead of `playwright-cli` when the global binary is not on PATH.

### 2. Playwright MCP (fallback for MCP-only clients)

Check whether Playwright MCP tools are available (e.g. `browser_navigate`, `browser_snapshot`, `browser_evaluate`, `browser_network_requests`).

If missing, tell the user to install [Playwright MCP](https://playwright.dev/docs/getting-started-mcp):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    }
  }
}
```

Or install **Playwright** from the [Cursor Marketplace](https://cursor.com/marketplace).

### 3. Neither available

If neither path works and the user cannot install one:

1. **Tell the user** that login sequences (multi-step login, 2FA) require browser automation.
2. Offer to install `playwright-cli` (preferred) or Playwright MCP.
3. Only if the user declines or installation fails, fall back to **form login** (Step 4) for simple single-page login forms.

**Never guess CSS/XPath selectors without browser inspection.**

## Target Type Check — Do This First

Before proceeding, determine whether this is an API target or a web target:

- If the user has provided an **OpenAPI/Swagger schema** (URL or file), a **Postman collection**, or explicitly said **"API target"** — stop and use the `saw-api-target-configuration` skill instead.
- Otherwise, **treat it as a web target by default**. If the user just says "add a target", "create a target", or provides a URL without further qualification, proceed here.

When you finish adding/configuring a target, always summarize it with a table, and include a link to the target on Snyk API & Web. Use the Snyk API & Web app URL **https://plus.probely.app**. Include a column if you added extra hosts or not and in case you did, which ones.

## Multiple Targets — Subagent Strategy

**When the user provides more than one target, launch a subagent per target.**

| Browser path | Subagent concurrency |
|---|---|
| **`playwright-cli`** | Subagents **may run in parallel** — each MUST use a **globally unique** session name: `playwright-cli -s=<session>`. Do NOT use the bare domain, since multiple targets can share one hostname (duplicate-URL flows, multiple accounts on one app) and would collide into a shared browser context. Use `<domain>-<targetIndex>` (e.g. `app.example.com-1`, `app.example.com-2`), appending the account/username when several targets share a domain. |
| **Playwright MCP** | Subagents **must run one at a time** — Playwright MCP uses a single shared browser instance |

Each subagent prompt should be short — just the target details and an instruction to read the skill file:

```
Configure a Snyk API & Web web target:
- URL: <url>
- Name: <name or "auto" — if "auto", derive from the site's <title>>
- Labels: <["Label1", ...] or "default" — if "default", do NOT pass labels param>
- Username: <user>
- Password: <pass>
- 2FA TOTP seed: <seed or "none">
- Browser session name: <session> (playwright-cli only — a globally unique name such as `<domain>-<targetIndex>`, plus the account/username when targets share a domain; use with `playwright-cli -s=<session>` for ALL browser commands)

First read the skill file at <ABSOLUTE_PATH_TO_THIS_SKILL_FILE> and follow the full workflow.
Return a summary with: target ID, name, URL, login sequence status, logout detection status, extra hosts, Snyk API & Web link (https://plus.probely.app/targets/{targetId}).
```

After all subagents finish, compile summaries into one table.

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
  is_sensitive=True
)
# cred["uri"] → "credentials://xxxx"
```

**Credential URIs:** Use the format `credentials://<credential_id>` (e.g., `credentials://4DY4qGohso1r`).
Get credential URIs from `probely_list_credentials` or `probely_create_credential`.
**Do NOT use template syntax like `{{cred-name}}`.**

### Browser Session Isolation (`playwright-cli` only)

Each target MUST use a **globally unique named session** (`-s=<session>`) for fully isolated browser context (separate cookies, storage, network logs). Never reuse the bare `<domain>` as the session name: multiple targets can share a hostname (duplicate-URL flows, multiple accounts on one app), and colliding names make parallel subagents share one browser context. Build the name from the domain plus a discriminator, e.g. `<domain>-<targetIndex>` or `<domain>-<username>` (such as `app.example.com-alice`, `app.example.com-bob`).

### Shell Timeout (`playwright-cli` only)

The Shell tool defaults to a 30-second timeout (`block_until_ms: 30000`), which is often too short for browser automation.

**ALWAYS set `block_until_ms: 60000` on Shell calls that run `playwright-cli`.** For slow targets/pages, use `block_until_ms: 90000`.

## Web Application Onboarding Workflow

### Step 1: Gather Information and Determine Authentication Method

Ask the user for (or derive):
1. **Target URL**
2. **Target name** (User provided > site `<title>` > FQDN)
3. **Labels** (Only pass if specified by user, do not add "Agentic")
4. **Login credentials**
5. **2FA/MFA requirements**

**Authentication method (in order):**
1. **Login sequence via `playwright-cli`** — preferred when Shell is available.
2. **Login sequence via Playwright MCP** — when CLI is unavailable but MCP browser tools exist.
3. **Form login** — fallback only when neither browser path is available.

#### Creating Duplicate Targets

To create a duplicate target (same URL as existing target), use `allow_duplicate=True`. This is useful when you want multiple targets for the same URL with different configurations (e.g., different authentication methods, different test scenarios):

```python
probely_create_web_target(
  name="MyApp - Different Auth Method",
  url="https://app.example.com",
  allow_duplicate=True
)
```

#### Reachability Failures

If target creation fails because the target is unreachable or the domain cannot be resolved, do not stop at the first error. Ask the user whether you should retry with `skip_reachability_check=True`. Only retry after the user explicitly agrees.

### Step 2A: Record Login Sequence — `playwright-cli` (preferred)

Use `playwright-cli` via the Shell tool. Set `block_until_ms: 60000` (or `90000` for slow pages).

1. **Open session and navigate:** `playwright-cli -s=SESSION open <url>`
2. **Find the login page** — use `snapshot` and `goto`.
3. **Inspect form elements** — run `scripts/inspect-login-form.js` via `playwright-cli -s=SESSION eval '<js>'`. Repeat on every login step.
4. **Fill credentials and submit** — use `snapshot` to get element refs, then `fill` and `click`. Refs (e.g. `e15`) or unique CSS selectors both work.
5. **Handle 2FA if needed** — use `probely_generate_totp` for the live OTP, then fill the OTP field.
6. **Verify login success** — record the absolute post-login URL (`eval '() => window.location.href'`).
7. **Verify login selectors are absent post-login** — use `eval`.
8. **Detect external API hosts (CRITICAL)** — read `references/extra-hosts.md`; run `playwright-cli -s=SESSION requests` at pre/post-login checkpoints.
9. **Generate login sequence JSON** — read `references/sequence-format.md`.
10. **Close session** — `playwright-cli -s=SESSION close`

Then apply SAW configuration (Step 3).

### Step 2B: Record Login Sequence — Playwright MCP (fallback)

Use when `playwright-cli` is unavailable but Playwright MCP tools exist.

1. **Navigate to target URL** — `browser_navigate`
2. **Find the login page** and record the URL.
3. **Inspect form elements** — run `scripts/inspect-login-form.js` via `browser_evaluate` on every login step.
4. **Fill credentials and submit** — record selectors for the sequence JSON.
5. **Handle 2FA if needed** — use `probely_generate_totp` for the live login.
6. **Verify login success** — record the absolute post-login URL for logout detection.
7. **Verify login selectors are NOT on the post-login page** — `browser_evaluate`.
8. **Detect external API hosts (CRITICAL)** — read `references/extra-hosts.md`; use `browser_network_requests()` at pre/post-login checkpoints.
9. **Generate login sequence JSON** — read `references/sequence-format.md`.

Then apply SAW configuration (Step 3).

### Step 3: Apply SAW Configuration (both browser paths)

```python
target = probely_create_web_target(name=..., url=..., desc=..., labels=...)  # use target["id"] as targetId

# If 2FA: call probely_configure_2fa_totp BEFORE creating the sequence (use otp_code in sequence JSON)

probely_create_credential(...)  # password — link via custom_field_mappings

probely_create_sequence(targetId, name="Login Sequence", content="...", sequence_type="login", enabled=True, custom_field_mappings=[...])

probely_configure_sequence_login(targetId, enabled=True)

# See references/logout-detection.md
probely_configure_logout_detection(targetId, enabled=True, check_session_url=..., logout_detector_type=..., logout_detector_value=..., logout_condition=...)

# See references/extra-hosts.md
probely_create_extra_host(targetId, hostname="...", ip_address="")
```

### Step 4: Form Login (no browser automation)

Use only when neither `playwright-cli` nor Playwright MCP is available, or the user explicitly accepts the limitation (no multi-step login, no 2FA).

By default, store the password via credential manager and pass the credential URI. If the user explicitly declines, pass the password inline.

```python
probely_configure_form_login(
  targetId,
  login_url="https://app.example.com/login",
  username_field="email",
  password_field="password",
  username="user@example.com",
  password="...",  # inline or cred URI
  check_pattern="Welcome"
)
```
