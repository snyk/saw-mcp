---
name: saw-web-target-configuration
description: Configure Snyk API&Web web application targets with authentication, login sequences, 2FA, and logout detection. Use when creating web app targets with form-based or sequence-based authentication.
---

# SAW Web Target Configuration Skill

Configure web application targets for Snyk API&Web (SAW/Probely) security scanning with authentication support. For API targets, use the `saw-api-target-configuration` skill instead.

When you finish adding/configuring a target, always summarize it with a table, and include a link to the target on SAW. Use the SAW app URL **https://plus.probely.app**. Include a column if you added extra hosts or not and in case you did, which ones.

## Multiple Targets — MUST Use Subagents

**When the user provides more than one target, you MUST launch a separate `generalPurpose` subagent for each target immediately.** Do NOT process targets one at a time yourself.

1. Read this skill file yourself first.
2. For **each** target, launch a `generalPurpose` subagent (via the Task tool) with a prompt that:
   - Includes the full contents of this skill file so the subagent follows the complete workflow.
   - Provides all known details for that target (URL, credentials, 2FA seed, name if given).
   - Tells the subagent to return a summary (target ID, name, URL, login sequence status, logout detection status, extra hosts, SAW link).
3. Launch **all** subagents in a **single message** so they run in parallel (up to 4 at a time; queue the rest).
4. After all subagents finish, compile their summaries into a single table for the user.

> **Why?** Each target's workflow (browser recording, API configuration) is independent. Parallelizing via subagents is faster and avoids the risk of a browser lock or error on one target blocking the others.

## Web Application Onboarding Workflow

When the user wants to scan a **web application with authentication**, follow this workflow:

### Step 1: Gather Information and Determine Authentication Method

Ask the user for (or derive):
1. **Target URL** (e.g., https://app.example.com)
2. **Target name**: use the name the user provides. **If the user does not specify a name**, use the site's `<title>` (e.g. from the login or home page when opened in Playwright). Example: no name given for https://patchmutual.com → **Patch Mutual**. A default label (e.g. "Agentic") is auto-applied from the MCP server config — **do NOT look up, create, or pass labels manually** unless the user explicitly asks for additional labels.
3. **Login credentials** (username/email and password)
4. Any **2FA/MFA requirements** (including the TOTP seed if applicable)

**Authentication method:** When Playwright MCP is available, **always configure authentication using a login sequence** (record the flow in the browser). Do not use form login when Playwright is available.

1. **Login Sequence** (use when Playwright is available) - Record the login in the browser; supports complex flows, 2FA, etc. **Prefer this whenever Playwright is available.**
2. **Form Login** (only when Playwright is NOT available) - Simple form-based auth for basic username/password pages.

### Step 2: Using Login Sequence (Playwright Available)

**If Playwright MCP server IS available**, use it to navigate and record the login sequence:

1. **Navigate to target URL** using Playwright
2. **Find the login page** - look for login links, buttons, or redirects. **Record the login page URL.**
3. **Inspect the current step's form elements** - run the inspection script (see below) to detect what's visible. The script auto-detects whether this is a single-page or multi-step login:
   - **Single-page login** (password field present): username, password, and submit are all returned at once.
   - **Multi-step login** (no password field): only the username/email and a "Next"/"Continue" button are returned. Fill the username, click next, then **run the inspection script again** on the second screen to get the password field and submit button.
4. **Fill credentials and submit** - for each step, fill the visible fields and click the step's button. Record selectors from each step for the login sequence JSON.
5. **Handle 2FA if needed** - if 2FA is required:
   - Use `probely_generate_totp(secret="THE_SEED")` to generate a TOTP code for the live Playwright login
   - Fill the OTP field with the returned **actual code** (e.g., "123456") to complete the login during recording
   - Later, when configuring the target, `probely_configure_2fa_totp` will auto-generate a fresh code for the sequence
6. **Verify login success and record post-login URL** - confirm login succeeded by checking for logged-in indicators. **IMPORTANT: Record the absolute URL you land on after successful login** (e.g., `https://example.com/dashboard`) - this will be used as the `check_session_url` for logout detection.
7. **Check for API calls to external hosts** - Use `browser_network_requests` to get all XHR/fetch requests made during login. Identify any requests to hostnames different from the target URL.
8. **Generate the login sequence JSON** - When creating the sequence JSON from the recorded steps:
   - Replace the actual username value with `[CUSTOM_USERNAME]` placeholder
   - Replace the actual password value with `[CUSTOM_PASSWORD]` placeholder
   - **Keep 2FA OTP codes hardcoded** (do NOT replace with custom fields)

**CRITICAL: Inspect Form Elements Before Creating Selectors**

Before generating the login sequence JSON, **always inspect the actual HTML elements** to get accurate selectors. Do NOT assume element types.

Use `browser_evaluate` to inspect form elements after navigating to the login page.

**Run this script on every step of the login flow.** It auto-detects the current step:
- If a password field is visible → **single-page login** (returns username + password + submit).
- If no password field → **multi-step login** (returns only the current step's input + button). After filling and clicking "Next", run it again on the next screen.

```javascript
() => {
  // Helpers
  const isStable = (id) => id && !/\d{3,}|[a-f0-9]{8,}/.test(id);
  const selectorFor = (el) => {
    if (!el) return null;
    if (el.name) return `${el.tagName.toLowerCase()}[name="${el.name}"]`;
    if (isStable(el.id)) return `#${el.id}`;
    if (el.type) return `${el.tagName.toLowerCase()}[type="${el.type}"]`;
    return null;
  };
  const describe = (el) => !el ? null : {
    tag: el.tagName, id: el.id, name: el.name, type: el.type,
    value: el.value, text: el.textContent?.trim()?.slice(0, 40),
    isStableId: isStable(el.id), selector: selectorFor(el)
  };
  const describeSubmit = (el) => {
    if (!el) return null;
    const d = describe(el);
    // For submit elements, prefer compound selectors when possible
    d.selector = el.name
      ? `${el.tagName.toLowerCase()}[type="${el.type || 'submit'}"][name="${el.name}"]`
      : d.selector;
    return d;
  };

  const passwordField = document.querySelector('input[type="password"]');

  // ── Single-page login: password field IS visible ──
  if (passwordField) {
    const form = passwordField.closest('form')
      || passwordField.closest('div, table, section, fieldset, main');

    let usernameField = null;
    if (form) {
      usernameField = form.querySelector(
        'input[type="text"], input[type="email"], input[name*="user"], input[name*="email"], input[name*="login"]'
      );
    }
    if (!usernameField) {
      const all = Array.from(document.querySelectorAll('input[type="text"], input[type="email"]'));
      usernameField = all.reverse().find(
        el => el.compareDocumentPosition(passwordField) & Node.DOCUMENT_POSITION_FOLLOWING
      );
    }

    let submitEl = null;
    if (form) {
      submitEl = form.querySelector('input[type="submit"], button[type="submit"], button:not([type])');
    }
    if (!submitEl) {
      const all = Array.from(document.querySelectorAll('input[type="submit"], button[type="submit"]'));
      submitEl = all.find(
        el => passwordField.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING
      ) || all[all.length - 1];
    }

    return {
      step: 'single_page',
      username: describe(usernameField),
      password: describe(passwordField),
      submit: describeSubmit(submitEl)
    };
  }

  // ── Multi-step login: no password field on this screen ──
  // Find the primary visible input (username/email) and the step's action button
  const candidates = Array.from(document.querySelectorAll(
    'input[type="text"], input[type="email"], input[name*="user"], input[name*="email"], input[name*="login"]'
  )).filter(el => el.offsetParent !== null); // visible only

  // Pick the most likely login input (prefer inputs inside a form, skip search boxes)
  let primaryInput = null;
  for (const el of candidates) {
    const inForm = el.closest('form');
    const looksLikeSearch = /search|query|q$/i.test(el.name || '') || /search|query|q$/i.test(el.id || '');
    if (!looksLikeSearch) { primaryInput = el; break; }
  }
  if (!primaryInput && candidates.length) primaryInput = candidates[0];

  const container = primaryInput
    ? (primaryInput.closest('form') || primaryInput.closest('div, table, section, fieldset, main'))
    : document.body;

  let stepButton = null;
  if (container) {
    stepButton = container.querySelector('input[type="submit"], button[type="submit"], button:not([type])');
  }
  if (!stepButton) {
    stepButton = document.querySelector('input[type="submit"], button[type="submit"]');
  }

  return {
    step: 'multi_step',
    note: 'No password field on this screen. Fill the input, click the button, then run this script again on the next screen.',
    input: describe(primaryInput),
    button: describeSubmit(stepButton)
  };
}
```

**Key Points:**
- **ALWAYS use the inspected CSS selectors** from the browser evaluation above - DO NOT guess or assume element types.
- Submit buttons can be any element that submits the form, including **`<button type="submit">`** OR **`<input type="submit">`** OR **`<span id="submit-form">Login</span>`** - always check the actual HTML!
- Prefer selectors with multiple attributes: `input[type="submit"][name="btnSubmit"]` is better than just `button[type="submit"]`
- **Avoid IDs that look random or generated** (e.g., `id="input-123456"`, `id="form-abc123xyz"`) - use **name attributes** (like `input[name="username"]`) or **stable IDs** (like `#uid`, `#login-btn`) instead.
- For each step that an input is filled in, save a click step before the "fill_value" to focus the input.

**XPath field:** The scanner uses CSS first; XPath is a fallback but must still be valid.
- Prefer attribute-based XPaths: `//*[@name='email']`, `//*[@id='uid']`
- Use positional XPaths (`/html/body/form/input[1]`) only as a last resort when the element has no usable attributes

After recording, generate the login sequence JSON and use the MCP tools below.

```
# 1. ALWAYS create a new target — do NOT search for or reuse existing targets, even if one with the same URL already exists.
# The default label (e.g. "Agentic") is auto-applied from config — no need to pass labels here.
# Only pass labels= if the user explicitly requests additional labels.
probely_create_target(name=..., url, desc?)

# 2. If 2FA is needed, configure it BEFORE creating the sequence.
# The tool auto-generates a TOTP code from the secret. Use the returned otp_code
# in the sequence's fill_value step for the OTP input.
result = probely_configure_2fa_totp(targetId, otp_secret="THE_SEED")
# result["otp_code"] → e.g. "829182" — use this in the sequence
#
# Build the COMPLETE sequence JSON (including the OTP fill step with the
# otp_code above) and pass it all to a single probely_create_sequence call.

# 3. Create the login sequence with custom field mappings for credentials
# Use [CUSTOM_USERNAME] and [CUSTOM_PASSWORD] placeholders in the sequence content.
# For 2FA, hardcode the otp_code from step 2 in the OTP fill_value step (do NOT use custom fields for OTP).
#
# COMMON MISTAKES — read before calling:
#   - content must be a JSON string of an array, e.g. "[{\"type\":\"goto\",...}]".
#     Do NOT double-serialize (string of a string).
#   - custom_field_mappings is REQUIRED when content uses [CUSTOM_USERNAME] or
#     [CUSTOM_PASSWORD]. Omitting it causes a 400 error.
probely_create_sequence(
  targetId,
  name="Login Sequence",
  content="[{...steps with [CUSTOM_USERNAME] and [CUSTOM_PASSWORD]...}]",
  sequence_type="login",
  enabled=True,
  custom_field_mappings=[
    {
      "name": "[CUSTOM_USERNAME]",
      "value": "actual_username_here",
      "value_is_sensitive": False,  # Set to True if username is sensitive
      "enabled": True
    },
    {
      "name": "[CUSTOM_PASSWORD]",
      "value": "actual_password_here",
      "value_is_sensitive": True,  # Always mark passwords as sensitive
      "enabled": True
    }
  ]
)

# 4. Enable sequence login on the target
probely_configure_sequence_login(targetId, enabled=True)

# 5. Configure logout detection - see "Configuring Logout Detection" section below for details
probely_configure_logout_detection(targetId, enabled=True, check_session_url=..., logout_detector_type=..., logout_detector_value=...)

# 6. If external API hosts were detected on the target URL or during the login flow, add them as extra hosts
probely_create_extra_host(targetId, hostname="api.example.com", ip_address="")
```

### Detecting and Configuring Extra Hosts

During login sequence recording, **always check for API calls to different hostnames**:

1. After completing the login flow, call `browser_network_requests()` to get all network requests
2. Parse the request URLs and extract hostnames
3. Compare each hostname against the target's primary hostname
4. If any XHR/fetch requests go to a different hostname (common patterns):
   - `api.example.com` vs `app.example.com`
   - `auth.example.com` vs `www.example.com`
5. For each different hostname found:
   - Use `probely_create_extra_host(targetId, hostname="api.example.com", ip_address="")`
   - **Inform the user**: "Detected API calls to `api.example.com` during login. Added as extra host."

Add only the hostnames from requests that seem to be related to the target. Exclude hostnames from vendor requests.

### Configuring Logout Detection

**Always configure logout detection** after setting up authentication:

1. **Identify the check session URL** - **IMPORTANT: Use the FULL URL you get redirected to immediately after a successful login.** This is the post-login landing page URL, NOT the login page URL or root URL.
   - Example: If login redirects to `/admin.php` or `/dashboard`, use the **full URL**: `https://app.example.com/admin.php`
   - This URL should return 200 when logged in, and 401/403 or redirect to login when logged out
   - **Record the FULL URL during the login sequence** - after clicking the login button and waiting for navigation, capture `window.location.href`
   - **ALWAYS use absolute URLs** (e.g., `https://app.example.com/dashboard`) - **NEVER use relative paths** (e.g., `/dashboard`)

2. **Use CSS selectors from the login form as logout detectors** - The best logout detectors are the CSS selectors you already recorded in the login sequence:
   - Username field selector (e.g., `input[placeholder='Enter Username...']`)
   - Password field selector (e.g., `input[type='password']`)
   - Use selectors or text that are only visible when the user is logged out. The selectors or text shouldn't exist on the page after the login. For text, the word "login" can be too common.
   
   If these elements appear on the page, it means the user was logged out.

3. **Configure it using the MCP tool** - **CRITICAL: You MUST explicitly provide both `logout_detector_type="sel"` and `logout_detector_value` parameters. Do NOT rely on automatic detection.**:
   ```
   probely_configure_logout_detection(
     targetId,
     enabled=True,
     check_session_url="https://app.example.com/dashboard",  # FULL URL (not "/dashboard")
     logout_detector_type="sel",  # REQUIRED - always use "sel" for CSS selectors
     logout_detector_value="#uid"  # REQUIRED - use the username field CSS selector from your login sequence
   )
   ```
   
   **Important**: Always use the **FULL URL** including protocol and domain (e.g., `https://app.example.com/dashboard`), NOT relative paths (e.g., `/dashboard`).

### Login Sequence JSON Format

The sequence format (based on the [Snyk API&Web Sequence Recorder](https://github.com/Probely/sequence-recorder)):

**IMPORTANT: Use Custom Fields for Credentials**

**Always use custom field placeholders for username and password** instead of hardcoding them in the sequence. This allows credentials to be managed separately and updated without modifying the sequence.

- Use `[CUSTOM_USERNAME]` placeholder for the username field
- Use `[CUSTOM_PASSWORD]` placeholder for the password field
- **2FA OTP codes should remain hardcoded** (see 2FA section below)

Example sequence with custom fields:

```json
[
  {
    "type": "goto",
    "timestamp": 1234567890000,
    "url": "https://app.example.com/login",
    "windowWidth": 1280,
    "windowHeight": 720,
    "urlType": "force"
  },
  { 
    "type": "click",
    "timestamp": 1234567891000,
    "css": "input[name='email']",
    "xpath": "//*[@name='email']",
    "value": "",
    "frame": null
  },
  {
    "type": "fill_value",
    "timestamp": 1234567892000,
    "css": "input[name='email']",
    "xpath": "//*[@name='email']",
    "value": "[CUSTOM_USERNAME]",
    "frame": null
  },
  { 
    "type": "click",
    "timestamp": 1234567893000,
    "css": "input[name='password']",
    "xpath": "/html/body/form/input[2]",
    "value": "",
    "frame": null
  },
  {
    "type": "fill_value",
    "timestamp": 1234567894000,
    "css": "input[name='password']",
    "xpath": "/html/body/form/input[2]",
    "value": "[CUSTOM_PASSWORD]",
    "frame": null
  },
  {
    "type": "click",
    "timestamp": 1234567895000,
    "css": "button[name='btnSubmit']",
    "xpath": "/html/body/form/button",
    "value": "Sign In",
    "frame": null
  }
]
```

**For 2FA**, use the `otp_code` returned by `probely_configure_2fa_totp` **hardcoded** in the sequence (do NOT use a custom field for OTP):
```json
{
  "type": "fill_value",
  "timestamp": 1234567896000,
  "css": "#otp",
  "xpath": "//*[@id='otp']",
  "value": "829182",
  "frame": null
}
```
Probely will automatically convert `fill_value` entries matching the configured OTP code to `fill_otp` type at scan time.

### Sequence Event Types

| Type | Description | Fields |
|------|-------------|--------|
| `goto` | Navigate to URL | `url`, `windowWidth`, `windowHeight`, `urlType` |
| `click` | Click an element | `css`, `xpath`, `value` (button text), `frame` |
| `dblclick` | Double-click | Same as click |
| `fill_value` | Enter text in input/textarea | `css`, `xpath`, `value` (text to enter), `frame` |
| `fill_otp` | Enter OTP code (auto-converted) | `css`, `xpath`, `value` (OTP code), `frame` |
| `change` | Checkbox/radio/select change | `css`, `xpath`, `subtype`, `checked`/`selected`, `frame` |
| `press_key` | Press a key | `css`, `xpath`, `value` (keyCode), `frame` |
| `mouseover` | Hover over element | `css`, `xpath`, `value`, `frame` |

### Step 3: Using Form Login (Playwright NOT Available)

**If Playwright MCP server is NOT available**, use form-based login:

```
probely_configure_form_login(
  targetId,
  login_url="https://app.example.com/login",
  username_field="email",
  password_field="password",
  username="user@example.com",
  password="secretpass",
  check_pattern="Welcome"
)
```

