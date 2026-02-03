---
name: saw-target-configuration
description: Configure Snyk API&Web (SAW/Probely) targets with authentication, 2FA, login sequences, and logout detection. Use when creating SAW targets, configuring login sequences, setting up TOTP/2FA, or working with probely_* MCP tools.
---

# SAW Target Configuration Skill

Detailed procedures for configuring Snyk API&Web targets. For behavioral rules (vulnerability handling, scan monitoring), see the project rules.
When you finish adding/configuring a target, always summarize it with a table, and include a link to the target on SAW, and a column if you added extra hosts or not and in case you did, which ones.

## API Onboarding Workflow

When the user wants to scan an **API**, follow this workflow:

### Step 1: Obtain API Schema

Ask the user to provide **one of** the following (they are alternatives):
1. **OpenAPI/Swagger schema** (URL or JSON/YAML file)
2. **Postman collection** (URL or JSON file)

If neither is available, offer to **generate an OpenAPI schema** by:
- Analyzing the codebase for API endpoints
- Looking for existing route definitions (Express, FastAPI, Flask, Django, etc.)
- Creating a basic OpenAPI 3.0 schema from discovered endpoints

### Step 2: Create API Target

**For Postman collections:**
```
probely_create_api_target_from_postman(
  name: "API Name",
  target_url: "https://api.example.com",
  postman_collection_url: "https://..." OR postman_collection_json: {...},
  desc: "Description",
  labels: ["api", "project-name"]
)
```

**For OpenAPI schemas:**
```
probely_create_api_target_from_openapi(
  name: "API Name",
  target_url: "https://api.example.com",
  openapi_schema_url: "https://..." OR openapi_schema_json: {...},
  desc: "Description",
  labels: ["api", "project-name"]
)
```

### Step 3: Configure API Authentication (if needed)

If the API requires authentication:
- Ask user for auth type (API key, Bearer token, OAuth, Basic Auth)
- Use `probely_update_target_settings` to configure authentication headers

## Web Application Onboarding Workflow

When the user wants to scan a **web application with authentication**, follow this workflow:

### Step 1: Gather Information

Ask the user for:
1. **Target name** (e.g., "My Web App - Production")
2. **Target URL** (e.g., https://app.example.com)
3. **Login credentials** (username/email and password)
4. Any **2FA/MFA requirements** (including the TOTP seed if applicable)

### Step 2: Choose Authentication Method

There are two ways to configure authentication:

1. **Login Sequence** (recommended when Playwright is available) - Records browser interactions for complex login flows, multi-step authentication, 2FA, etc.
2. **Form Login** (simpler, use when Playwright is NOT available) - Simple form-based authentication for basic username/password login pages.

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
6. **Verify login success and record post-login URL** - confirm login succeeded by checking for logged-in indicators. **IMPORTANT: Record the URL you land on after successful login** (e.g., `/dashboard`, `/admin.php`, `/home`) - this will be used as the `check_session_url` for logout detection.
7. **Check for API calls to external hosts** - Use `browser_network_requests` to get all XHR/fetch requests made during login. Identify any requests to hostnames different from the target URL.
8. **Generate the login sequence JSON** - When creating the sequence JSON from the recorded steps:
   - Replace the actual username value with `[CUSTOM_USERNAME]` placeholder
   - Replace the actual password value with `[CUSTOM_PASSWORD]` placeholder
   - **Keep 2FA OTP codes hardcoded** (do NOT replace with custom fields)

Notes when creating the login sequence:
- For each step that an input is filled in, save a click step before the “fill_value” to focus the input.
- Use the best unique CSS selector for each element. Using button[type="submit"] is too common. Combine it with other element attributes, like the id or data-test and/or selectors from parent elements, like form#login-form input[name="username"]. 

After recording, generate the login sequence JSON and use these MCP tools:

```
# 1. Create the target
probely_create_target(name, url, desc?)

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
# Use the post-login redirect URL recorded in step 6 above (NOT the root URL or login page)
probely_configure_logout_detection(targetId, enabled=True, check_session_url="/dashboard")  # The URL you landed on after login

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

1. **Identify the check session URL** - **IMPORTANT: Use the URL you get redirected to immediately after a successful login.** This is the post-login landing page URL, NOT the login page URL or root URL.
   - Example: If login redirects to `/admin.php` or `/dashboard`, use that URL
   - This URL should return 200 when logged in, and 401/403 or redirect to login when logged out
   - **Record this URL during the login sequence** - after clicking the login button and waiting for navigation, capture the current URL
   - Use the absolute URL (e.g., `https://app.example.com/dashboard`)

2. **Use CSS selectors from the login form as logout detectors** - The best logout detectors are the CSS selectors you already recorded in the login sequence:
   - Username field selector (e.g., `input[placeholder='Enter Username...']`)
   - Password field selector (e.g., `input[type='password']`)
   - Use selectors or text that are only visible when the user is logged out. The selectors or text shouldn’t exist on the page after the login. For text, the word “login” can be too common.
   
   If these elements appear on the page, it means the user was logged out.

3. **Configure it using the MCP tool**:
   ```
   probely_configure_logout_detection(
     targetId,
     enabled=True,
     check_session_url="https://app.example.com/dashboard",  # The post-login redirect URL
     logout_detector_type="sel",
     logout_detector_value="input[placeholder='Enter Username...']"
   )
   ```

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

### API Target Creation
- `probely_create_api_target_from_postman(...)` - Create from Postman
- `probely_create_api_target_from_openapi(...)` - Create from OpenAPI
