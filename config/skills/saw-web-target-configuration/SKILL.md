---
name: saw-web-target-configuration
description: Configure Snyk API&Web web application targets with authentication, login sequences, 2FA, and logout detection. Use when creating web app targets with form-based or sequence-based authentication.
---

# SAW Web Target Configuration Skill

Configure web application targets for Snyk API&Web (SAW/Probely) security scanning with authentication support. For API targets, use the `saw-api-target-configuration` skill instead.

When you finish adding/configuring a target, always summarize it with a table, and include a link to the target on SAW. Use the SAW app URL **https://plus.probely.app**. Include a column if you added extra hosts or not and in case you did, which ones.

## Web Application Onboarding Workflow

When the user wants to scan a **web application with authentication**, follow this workflow:

### Step 1: Gather Information

Ask the user for (or derive):
1. **Target URL** (e.g., https://app.example.com)
2. **Target name**: use the name the user provides; if none, use **Agentic - &lt;web page title&gt;** (page title from the site's `<title>` when you open it in Playwright).
3. **Login credentials** (username/email and password)
4. Any **2FA/MFA requirements** (including the TOTP seed if applicable)

### Step 2: Target name and authentication method

**Target name:** Use the name the user provides in the prompt. **If the user does not specify a name**, use **Agentic - &lt;web page title&gt;** where the page title is the site's `<title>` (e.g. from the login or home page when opened in Playwright). Example: no name given for https://patchmutual.com → **Agentic - Patch Mutual**.

**Authentication:** When Playwright MCP is available, **always configure authentication using a login sequence** (record the flow in the browser). Do not use form login when Playwright is available.

1. **Login Sequence** (use when Playwright is available) - Record the login in the browser; supports complex flows, 2FA, etc. **Prefer this whenever Playwright is available.**
2. **Form Login** (only when Playwright is NOT available) - Simple form-based auth for basic username/password pages.

### Step 3A: Using Login Sequence (Playwright Available)

**If Playwright MCP server IS available**, use it to navigate and record the login sequence:

1. **Navigate to target URL** using Playwright
2. **Find the login page** - look for login links, buttons, or redirects. **Record the login page URL.**
3. **Identify login form elements** - get the CSS selectors for username, password fields, and submit button
4. **Fill credentials and submit** - enter the provided credentials and click submit
5. **Handle 2FA if needed** - if 2FA is required:
   - **Generate the actual TOTP code** from the seed using the standard TOTP algorithm (SHA1, 6 digits, 30-second window)
   - Fill the OTP field with this **actual generated code** (e.g., "123456"), NOT a placeholder
   - This allows the login to complete successfully during recording
6. **Verify login success and record post-login URL** - confirm login succeeded by checking for logged-in indicators. **IMPORTANT: Record the absolute URL you land on after successful login** (e.g., `https://example.com/dashboard`) - this will be used as the `check_session_url` for logout detection.
7. **Check for API calls to external hosts** - Use `browser_network_requests` to get all XHR/fetch requests made during login. Identify any requests to hostnames different from the target URL.
8. **Generate the login sequence JSON** - When creating the sequence JSON from the recorded steps:
   - Replace the actual username value with `[CUSTOM_USERNAME]` placeholder
   - Replace the actual password value with `[CUSTOM_PASSWORD]` placeholder
   - **Keep 2FA OTP codes hardcoded** (do NOT replace with custom fields)

**CRITICAL: Inspect Form Elements Before Creating Selectors**

Before generating the login sequence JSON, **always inspect the actual HTML elements** to get accurate selectors. Do NOT assume element types.

Use `browser_evaluate` to inspect form elements after navigating to the login page:

```javascript
() => {
  const usernameField = document.querySelector('input[type="text"], input[type="email"], input[name*="user"], input[name*="email"]');
  const passwordField = document.querySelector('input[type="password"]');
  
  // Find submit element (can be button OR input)
  const submitButton = document.querySelector('button[type="submit"]');
  const submitInput = document.querySelector('input[type="submit"]');
  const submitElement = submitButton || submitInput;
  
  return {
    username: {
      tag: usernameField?.tagName,
      id: usernameField?.id,
      name: usernameField?.name,
      type: usernameField?.type,
      // Check if ID looks random/generated (contains numbers, long strings)
      isStableId: usernameField?.id && !/\d{3,}|[a-f0-9]{8,}/.test(usernameField.id),
      selector: usernameField?.name ? `input[name="${usernameField.name}"]` :
                (usernameField?.id && !/\d{3,}|[a-f0-9]{8,}/.test(usernameField.id)) ? `#${usernameField.id}` : null
    },
    password: {
      tag: passwordField?.tagName,
      id: passwordField?.id,
      name: passwordField?.name,
      isStableId: passwordField?.id && !/\d{3,}|[a-f0-9]{8,}/.test(passwordField.id),
      selector: passwordField?.name ? `input[name="${passwordField.name}"]` :
                (passwordField?.id && !/\d{3,}|[a-f0-9]{8,}/.test(passwordField.id)) ? `#${passwordField.id}` : null
    },
    submit: {
      tag: submitElement?.tagName,
      type: submitElement?.type,
      id: submitElement?.id,
      name: submitElement?.name,
      value: submitElement?.value,
      isStableId: submitElement?.id && !/\d{3,}|[a-f0-9]{8,}/.test(submitElement.id),
      selector: submitElement?.name ? 
        `${submitElement.tagName.toLowerCase()}[type="submit"][name="${submitElement.name}"]` :
        (submitElement?.id && !/\d{3,}|[a-f0-9]{8,}/.test(submitElement.id)) ? `#${submitElement.id}` :
        `${submitElement.tagName.toLowerCase()}[type="submit"]`
    }
  };
}
```

**Key Points:**
- Submit buttons can be **`<button type="submit">`** OR **`<input type="submit">`** - always check the actual HTML!
- Use the inspected selectors (from the evaluation above) in your sequence JSON
- Prefer selectors with multiple attributes: `input[type="submit"][name="btnSubmit"]` is better than just `button[type="submit"]`
- **Avoid IDs that look random or generated** (e.g., `id="input-123456"`, `id="form-abc123xyz"`) - these may change between page loads
- Use **stable IDs** (like `#uid`, `#password`, `#login-btn`) or **name attributes** (like `input[name="username"]`) - these are most reliable

Notes when creating the login sequence:
- For each step that an input is filled in, save a click step before the "fill_value" to focus the input.
- **ALWAYS use the inspected CSS selectors** from the browser evaluation above - DO NOT guess or assume element types.
- Prefer multi-attribute selectors: `input[type="submit"][name="btnSubmit"]` instead of generic `button[type="submit"]`.
- Use stable ID-based selectors (like `#uid`, `#login-btn`) only when the ID is semantic and unlikely to change - avoid random/generated IDs.

After recording, generate the login sequence JSON and use these MCP tools:

```
# 1. Create the target (if user didn't specify a name, use "Agentic - <Page Title>" from the page's <title>)
probely_create_target(name=..., url, desc?)

# 2. Create the login sequence with custom field mappings for credentials
# IMPORTANT: Use [CUSTOM_USERNAME] and [CUSTOM_PASSWORD] placeholders in the sequence content
# NOTE: For 2FA, use the actual generated OTP code hardcoded in the sequence (do NOT use custom fields)
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
      "value": "actual_password_here",
      "value_is_sensitive": True,  # Mark password as sensitive
      "enabled": True
    }
  ]
)

# 3. Enable sequence login on the target
probely_configure_sequence_login(targetId, enabled=True)

# 4. If 2FA is needed, configure it:
# - Use the actual OTP code from the sequence as the placeholder (so Probely knows what to replace)
probely_configure_2fa(targetId, otp_secret="THE_SEED", otp_placeholder="123456")  # The same code used in the sequence

# 5. Configure logout detection (IMPORTANT!)
# CRITICAL: ALWAYS provide logout_detector_type="sel" and logout_detector_value with the username field selector
# Use the FULL post-login redirect URL (not relative path) recorded in step 6 above
probely_configure_logout_detection(
  targetId, 
  enabled=True, 
  check_session_url="https://app.example.com/dashboard",  # FULL URL - not just "/dashboard"
  logout_detector_type="sel",  # REQUIRED - do not omit this
  logout_detector_value="#uid"  # REQUIRED - username field CSS selector from login sequence
)

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
    "timestamp": 1234567890,
    "url": "https://app.example.com/login",
    "windowWidth": 1280,
    "windowHeight": 720,
    "urlType": "force"
  },
  { 
    "type": "click",
    "timestamp": 1234567891,
    "css": "input[name='email']",
    "xpath": "/html/body/form/input[1]",
    "value": "",
    "frame": null
  },
  {
    "type": "fill_value",
    "timestamp": 1234567892,
    "css": "input[name='email']",
    "xpath": "/html/body/form/input[1]",
    "value": "[CUSTOM_USERNAME]",
    "frame": null
  },
  { 
    "type": "click",
    "timestamp": 1234567893,
    "css": "input[name='password']",
    "xpath": "/html/body/form/input[2]",
    "value": "",
    "frame": null
  },
  {
    "type": "fill_value",
    "timestamp": 1234567894,
    "css": "input[name='password']",
    "xpath": "/html/body/form/input[2]",
    "value": "[CUSTOM_PASSWORD]",
    "frame": null
  },
  {
    "type": "click",
    "timestamp": 1234567895,
    "css": "button[type='submit']",
    "xpath": "/html/body/form/button",
    "value": "Sign In",
    "frame": null
  }
  // NOTE: If the submit button is an <input> instead of <button>, use:
  // "css": "input[type='submit'][name='btnSubmit']"
]
```

**Configure custom fields via API** when creating/updating the sequence using the `custom_field_mappings` parameter:

```python
custom_field_mappings=[
  {
    "name": "[CUSTOM_USERNAME]",
    "value": "user@example.com",
    "value_is_sensitive": False,
    "enabled": True
  },
  {
    "name": "[CUSTOM_PASSWORD]",
    "value": "password123",
    "value_is_sensitive": True,  # Always mark passwords as sensitive
    "enabled": True
  }
]
```

The platform will automatically replace `[CUSTOM_USERNAME]` and `[CUSTOM_PASSWORD]` placeholders in the sequence content with the configured values.

**For 2FA**, generate the actual TOTP code and use it **hardcoded** in the sequence (do NOT use a custom field):
```json
{
  "type": "fill_otp",
  "timestamp": 1234567894,
  "css": "#otp",
  "xpath": "//*[@id='otp']",
  "value": "783757",
  "frame": null
}
```

**IMPORTANT for 2FA configuration:**
- Generate the TOTP code using: seed + SHA1 algorithm + 6 digits + 30-second window
- Use this actual code **hardcoded** in the sequence (2FA OTP should NOT use custom fields)
- **CRITICAL ORDER**: Configure `probely_configure_2fa` with `otp_placeholder` set to the SAME code BEFORE updating/creating the sequence
- Probely will automatically convert `fill_value` entries matching the OTP placeholder to `fill_otp` type

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

### Step 3B: Using Form Login (Playwright NOT Available)

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

**IMPORTANT**: Form login does NOT support 2FA. If the application requires 2FA, you MUST use login sequences with Playwright.

## Available MCP Tools Reference

### Target Management
- `probely_list_targets(search?)` - List all targets
- `probely_get_target(targetId)` - Get target details
- `probely_create_target(name, url, desc?, label_ids?)` - Create new target
- `probely_update_target(targetId, name?, url?, desc?, label_ids?)` - Update target
- `probely_delete_target(targetId)` - Delete target

### Login Sequences
- `probely_list_sequences(targetId)` - List all login sequences
- `probely_get_sequence(targetId, sequenceId)` - Get sequence details
- `probely_create_sequence(targetId, name, content, sequence_type?, enabled?, custom_field_mappings?)` - Create sequence with custom field mappings for credentials
- `probely_update_sequence(targetId, sequenceId, name?, content?, enabled?, custom_field_mappings?)` - Update sequence, including custom field mappings

### Authentication Configuration
- `probely_configure_form_login(...)` - Configure form-based login
- `probely_configure_sequence_login(targetId, enabled?)` - Enable/disable sequence login
- `probely_configure_2fa(targetId, otp_secret, otp_placeholder?, ...)` - Configure 2FA/TOTP
- `probely_disable_2fa(targetId)` - Disable 2FA
- `probely_configure_logout_detection(targetId, enabled?, check_session_url?, ...)` - Configure logout detection
- `probely_create_logout_detector(targetId, detector_type, value)` - Create logout detector

### Scanning
- `probely_list_scans(targetId)` - List scans
- `probely_get_scan(targetId, scanId)` - Get scan details
- `probely_start_scan(targetId, profile?)` - Start scan (only when user requests)
- `probely_stop_scan(targetId, scanId)` - Stop scan
- `probely_cancel_scan(targetId, scanId)` - Cancel scan

### Findings
- `probely_list_findings(targetId, severity?, state?)` - List findings
- `probely_get_finding(targetId, findingId)` - Get finding details
- `probely_update_finding(targetId, findingId, state?)` - Update finding
- `probely_bulk_update_findings(targetId, findingIds, state?)` - Bulk update

### Reports
- `probely_create_scan_report(scanId, report_type?, format?)` - Create report
- `probely_download_report(reportId)` - Download report
- `probely_get_report(reportId)` - Get report status

### Extra Hosts
- `probely_list_extra_hosts(targetId)` - List extra hosts
- `probely_create_extra_host(targetId, hostname, ip_address)` - Add extra host
- `probely_update_extra_host(targetId, extraHostId, hostname?, ip_address?)` - Update extra host

### Labels
- `probely_list_labels()` - List all labels
- `probely_create_label(name, color?)` - Create label
