---
name: saw-web-target-configuration
description: Configure Snyk API&Web web application targets with authentication, login sequences, 2FA, and logout detection. Use when creating web app targets with form-based or sequence-based authentication.
---

# SAW Web Target Configuration Skill

Configure web application targets for Snyk API&Web (SAW/Probely) security scanning with authentication support. For API targets, use the `saw-api-target-configuration` skill instead.

When you finish adding/configuring a target, always summarize it with a table, and include a link to the target on SAW. Use the SAW app URL **https://plus.probely.app**. Include a column if you added extra hosts or not and in case you did, which ones.

## Multiple Targets — MUST Use Subagents in Parallel

**When the user provides more than one target, you MUST launch ALL subagents in a single message.**

Each subagent prompt should be short — just the target details and an instruction to read the skill file:

```
Configure a Snyk API&Web web target:
- URL: <url>
- Name: <name or "auto" — if "auto", derive from the site's <title>>
- Labels: <["Label1", ...] or "default" — if "default", do NOT pass labels param>
- Username: <user>
- Password: <pass>
- 2FA TOTP seed: <seed or "none">

First, read the skill file at <ABSOLUTE_PATH_TO_THIS_SKILL_FILE> and follow the full workflow.
Return a summary with: target ID, name, URL, login sequence status, logout detection status, extra hosts, SAW link (https://plus.probely.app/targets/{targetId}).
```

**Do NOT embed the full skill text in each prompt** — that makes prompts too large to launch in parallel. Each subagent can read the skill file itself.

Launch **all** Task tool calls in a **single assistant message** (max 10 at a time). Do NOT wait for one to finish before launching the next. After all finish, compile summaries into one table.

## Web Application Onboarding Workflow

When the user wants to scan a **web application with authentication**, follow this workflow:

### Step 1: Gather Information and Determine Authentication Method

Ask the user for (or derive):
1. **Target URL** (e.g., https://app.example.com)
2. **Target name** (resolved in priority order):
   1. Use the name the user provides, if any.
   2. Otherwise, use the site's `<title>` tag (e.g. from the login or home page when opened in Playwright).
   3. If the page has no `<title>`, use the FQDN of the target URL (e.g. `app.example.com`).
   
   **NEVER use a label value as the target name.**
3. **Labels**: If the user specifies labels, pass **only those labels** via `labels=[...]` when creating the target — do NOT add the default "Agentic" label. If the user does NOT specify any labels, do NOT pass `labels` at all (the default label is auto-applied from the MCP server config).
4. **Login credentials** (username/email and password)
5. Any **2FA/MFA requirements** (including the TOTP seed if applicable)

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
7. **Verify login selectors are NOT on the post-login page** - After login succeeds, check whether the CSS selectors used in the login sequence (e.g., username/password fields) still exist on the post-login page. Use `browser_evaluate` to test each selector:
   ```javascript
   () => ({
     usernameExists: !!document.querySelector("input[name='username']"),
     passwordExists: !!document.querySelector("input[name='password']")
   })
   ```
   If any selector **still exists** after login (e.g., a read-only username field on a profile section), record this — you will need it to pick a proper `check_session_url` and a more specific logout detector (see "Configuring Logout Detection" below).
8. **Detect external API hosts (CRITICAL)** - Follow the full procedure in "Detecting and Configuring Extra Hosts" below. This step is **mandatory** — do NOT skip it even if browser calls fail. Use the multi-layered detection approach (network requests + JavaScript introspection) to identify any hostnames different from the target URL.
9. **Generate the login sequence JSON** - When creating the sequence JSON from the recorded steps:
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
# Labels: If the user specified labels, pass ONLY those via labels=[...] (do NOT add "Agentic").
#         If the user did NOT specify labels, omit the labels param entirely (the default is auto-applied from config).
# Name: Use user-provided name > site <title> > FQDN. NEVER use a label as the name.
target = probely_create_target(name=..., url, desc?, labels?)
# IMPORTANT: Use target["id"] (the top-level ID) as targetId for ALL subsequent calls.
# Do NOT use target["site"]["id"] — that is a different internal ID and will cause 404 errors.

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
# PASSWORD: Use credentials management — create a credential first, then link it
# via its URI. Do NOT store the password inline in custom_field_mappings.
cred = probely_create_credential(
  name="<target_name> - <username> password",  # e.g. "MyApp - jane@example.com password"
  value="actual_password_here",
  is_sensitive=True
)
# cred["uri"] → e.g. "credentials://doXJZdwvj1vW" — use this as the "value" for [CUSTOM_PASSWORD]
#
# USERNAME: Use inline value (typically not sensitive).
#
# NOTE: custom_field_mappings is REQUIRED when content uses [CUSTOM_USERNAME] or
# [CUSTOM_PASSWORD]. Omitting it causes a 400 error from the API.
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
      "value_is_sensitive": False,
      "enabled": True
    },
    {
      "name": "[CUSTOM_PASSWORD]",
      "value": cred["uri"],       # Link credential via its URI (e.g. "credentials://xxxx")
      "value_is_sensitive": True,
      "enabled": True
    }
  ]
)

# 4. Enable sequence login on the target
probely_configure_sequence_login(targetId, enabled=True)

# 5. Configure logout detection - see "Configuring Logout Detection" section below for details
# logout_condition defaults to 'any' (OR). Use 'all' (AND) when some detectors match even when logged in.
probely_configure_logout_detection(targetId, enabled=True, check_session_url=..., logout_detector_type=..., logout_detector_value=..., logout_condition=...)

# 6. If external API hosts were detected on the target URL or during the login flow, add them as extra hosts
probely_create_extra_host(targetId, hostname="api.example.com", ip_address="")
```

### Detecting and Configuring Extra Hosts

Extra host detection is **CRITICAL** — missing an API host means the scanner cannot test those endpoints. Use a **multi-layered approach** with retries and fallbacks to ensure no hosts are missed.

#### Layer 1: Network request capture (primary method, with retries)

Capture network requests at **two checkpoints** during the login flow:

1. **After initial page navigation** (before login) — call `browser_network_requests()` right after navigating to the target URL and the login page loads. Some apps make API calls on page load.
2. **After login completes** — call `browser_network_requests()` again after successful login. Login and post-login pages often trigger additional API calls.

**If `browser_network_requests()` fails at any checkpoint, retry it up to 2 more times** (3 attempts total). Take a `browser_snapshot` between retries to re-stabilize the session. Do NOT skip this step on failure — exhaust all retries first.

From the collected requests, extract hostnames and compare against the target's primary hostname. Common patterns:
- `api.example.com` vs `app.example.com` or `example.com`
- `auth.example.com` vs `www.example.com`
- `backend.example.com` vs `example.com`

#### Layer 2: JavaScript introspection (fallback)

**Always run this as a secondary check**, even if Layer 1 succeeded. Use `browser_evaluate` on the post-login page to discover API base URLs embedded in the page's JavaScript context:

```javascript
() => {
  const found = new Set();
  const targetHost = location.hostname;

  const extractHosts = (str) => {
    const matches = str.match(/https?:\/\/[a-zA-Z0-9][-a-zA-Z0-9.]*[a-zA-Z0-9](?::\d+)?/g);
    if (matches) matches.forEach(u => {
      try {
        const h = new URL(u).hostname;
        if (h !== targetHost && h.endsWith(targetHost.replace(/^www\./, '').replace(/^[^.]+\./, '')))
          found.add(h);
      } catch {}
    });
  };

  // Next.js embedded data
  if (window.__NEXT_DATA__) extractHosts(JSON.stringify(window.__NEXT_DATA__));

  // Environment / config globals (common patterns)
  for (const key of Object.keys(window)) {
    if (/env|config|settings|api/i.test(key)) {
      try { extractHosts(JSON.stringify(window[key])); } catch {}
    }
  }

  // Inline and external script contents
  document.querySelectorAll('script:not([src])').forEach(s => extractHosts(s.textContent));

  // Meta tags (some apps store API URLs here)
  document.querySelectorAll('meta[content*="http"]').forEach(m => extractHosts(m.content));

  return { apiHosts: [...found], targetHost };
}
```

Merge the results from Layer 2 with any hosts found in Layer 1.

#### Filtering and adding extra hosts

From the combined results of both layers:
- **Include** hostnames that share the same base domain as the target (e.g., `api.example.com` for a target at `example.com`).
- **Exclude** unrelated third-party/vendor hostnames (e.g., `cdn.jsdelivr.net`, `fonts.googleapis.com`, `analytics.google.com`).

For each relevant hostname found:
```
probely_create_extra_host(targetId, hostname="api.example.com", ip_address="")
```

**Always report** what was detected: "Detected API calls to `api.example.com`. Added as extra host."

If both layers returned zero extra hosts, report: "No external API hosts detected (checked via network requests and JS introspection)."

### Configuring Logout Detection

**Always configure logout detection** after setting up authentication.

The login form selectors you recorded may also exist on the post-login page (e.g., a read-only username field on a profile section, or a password field inside a "change password" form). If you don't account for this, the scanner will think it's always logged out and fail. **Step 7 above detects this.** Use the guidance below to handle it.

#### 1. Pick the `check_session_url`

- **Default**: Use the **FULL absolute URL** you land on immediately after login (e.g., `https://app.example.com/dashboard`). Record it via `window.location.href` during the login sequence.
- **If login selectors still exist on the post-login landing page**: Pick a **different authenticated URL** where those selectors do NOT exist — for example a `/settings`, `/profile`, or `/dashboard` page. Browse the post-login page during recording to find a suitable link.
- **ALWAYS use absolute URLs** (e.g., `https://app.example.com/settings`) — **NEVER relative paths** (e.g., `/settings`).

#### 2. Pick the logout detector

The best logout detectors are CSS selectors from the login form. But they **must only exist when logged out**.

- **If the selector does NOT exist on the post-login page** (the common case): use it directly.
  ```
  logout_detector_type="sel"
  logout_detector_value="input[name='username']"
  ```
- **If the selector DOES exist on the post-login page** (detected in step 7): use a **more specific CSS selector** that includes a parent element unique to the login form. For example, if the login form has `id="formlogin"`:
  ```
  logout_detector_type="sel"
  logout_detector_value="#formlogin input[name='username']"
  ```
  Or scope via the form's action, a wrapping div, etc. The goal is a selector that **only matches the login form**, not the logged-in profile/settings page.

- **`logout_condition` parameter** — controls how multiple detectors combine:
  - `"any"` (default, OR): logged out if **ANY** detector matches. Use when each detector uniquely identifies the logged-out state.
  - `"all"` (AND): logged out only if **ALL** detectors match. Use as a **fallback** when you cannot craft a selector specific enough to avoid the post-login page. Add a second unambiguous detector (e.g., text that only appears on the login page) and set `logout_condition="all"` so both must match.

#### 3. Configure via the MCP tool

**CRITICAL: You MUST explicitly provide both `logout_detector_type` and `logout_detector_value`. Do NOT rely on automatic detection.**

```
probely_configure_logout_detection(
  targetId,
  enabled=True,
  check_session_url="https://app.example.com/dashboard",  # FULL absolute URL
  logout_detector_type="sel",    # REQUIRED
  logout_detector_value="#uid",  # REQUIRED — must NOT match when logged in
  logout_condition="any"         # "any" (default) or "all"
)
```

**Important**: Always use the **FULL URL** including protocol and domain (e.g., `https://app.example.com/dashboard`), NOT relative paths (e.g., `/dashboard`).

### Login Sequence JSON Format

The sequence format (based on the [Snyk API&Web Sequence Recorder](https://github.com/Probely/sequence-recorder)):

**IMPORTANT: Use Custom Fields for Credentials**

**Always use custom field placeholders for username and password** instead of hardcoding them in the sequence.

- Use `[CUSTOM_USERNAME]` placeholder for the username field — map to inline `value` in custom_field_mappings
- Use `[CUSTOM_PASSWORD]` placeholder for the password field — **create a credential** via `probely_create_credential`, then pass its `uri` (e.g. `credentials://xxxx`) as the `value` in custom_field_mappings. Do NOT store the password inline.
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

