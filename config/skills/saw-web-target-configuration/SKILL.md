---
name: saw-web-target-configuration
description: Configure Snyk API & Web web application targets with authentication, login sequences, 2FA, and logout detection. Use when creating web app targets with form-based or sequence-based authentication.
---

# SAW Web Target Configuration Skill

Configure web application targets for Snyk API & Web (SAW/Probely) security scanning with authentication support. For API targets, use the `saw-api-target-configuration` skill instead.

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

First, read the skill file at <ABSOLUTE_PATH_TO_THIS_SKILL_FILE> and follow the full workflow.
Return a summary with: target ID, name, URL, login sequence status, logout detection status, extra hosts, SAW link (https://plus.probely.app/targets/{targetId}).
```

Launch **all** Task tool calls in a **single assistant message** (max 10 at a time). Do NOT wait for one to finish before launching the next. After all finish, compile summaries into one table.

## Credentials Management — Optional; Do Not Apply by Default

Credentials management is **supported** but must **not** be applied automatically. **Prompt the user** to choose whether to use the credential manager for sensitive values. Only when the user opts in should you store values via `probely_create_credential` and use the returned `uri` (e.g. `credentials://xxxx`) in the API.

## Web Application Onboarding Workflow

### Step 1: Gather Information and Determine Authentication Method

Ask the user for (or derive):
1. **Target URL**
2. **Target name** (User provided > site `<title>` > FQDN)
3. **Labels** (Only pass if specified by user, do not add "Agentic")
4. **Login credentials**
5. **2FA/MFA requirements**

**Authentication method:** 
1. **Login Sequence** (use when Playwright is available) - Record the login in the browser. **Prefer this.**
2. **Form Login** (only when Playwright is NOT available) - Simple form-based auth.

### Step 2: Using Login Sequence (Playwright Available)

1. **Navigate to target URL** using Playwright
2. **Find the login page** and record the URL.
3. **Inspect the current step's form elements** - run `scripts/inspect-login-form.js` via `browser_evaluate` to detect what's visible. Run this on every step of the login flow.
4. **Fill credentials and submit** - record selectors for the login sequence JSON.
5. **Handle 2FA if needed** - use `probely_generate_totp` to get a code for the live login.
6. **Verify login success** - **Record the absolute URL you land on after successful login** for logout detection.
7. **Verify login selectors are NOT on the post-login page** - test if login selectors still exist using `browser_evaluate`.
8. **Detect external API hosts (CRITICAL)** - Read `references/extra-hosts.md` for instructions on using network requests and `scripts/extract-api-hosts.js` to find extra hosts.
9. **Generate the login sequence JSON** - Read `references/sequence-format.md` for the correct JSON format using custom fields.
10. **Enable authentication with login sequence** - call `probely_configure_sequence_login(targetId, enabled=True)`.

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

### Step 3: Using Form Login (Playwright NOT Available)

If the user opted in to credentials management, store the password via credential manager and pass the credential URI. Otherwise pass the password inline.

```python
probely_configure_form_login(
  targetId,
  login_url="https://app.example.com/login",
  username_field="email",
  password_field="password",
  username="user@example.com",
  password="...", # inline or cred URI
  check_pattern="Welcome"
)
```