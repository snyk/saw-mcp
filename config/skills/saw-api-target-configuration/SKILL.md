---
name: saw-api-target-configuration
description: Configure Snyk API & Web API targets. Use ONLY when the user explicitly provides or mentions an OpenAPI/Swagger schema, a Postman collection, or explicitly says "API target". Do NOT use for generic "add target" or "create target" requests — use saw-web-target-configuration instead.
---

# API Target Configuration Skill (Snyk API & Web)

Configure API targets for Snyk API & Web security scanning. For web application targets with authentication, use the `saw-web-target-configuration` skill instead.

When you finish adding/configuring a target, always summarize it with a table, and include a link to the target on Snyk API & Web. Use the Snyk API & Web app URL **https://plus.probely.app**. Include a column if you added extra hosts or not and in case you did, which ones.

## Credentials Management — Recommended (Used by Default)

Use the credential manager for sensitive values (API keys, Bearer tokens, Basic Auth passwords, etc.) by default. Store values via `probely_create_credential` with `is_sensitive=True` and use the returned `uri` (e.g. `credentials://xxxx`) in the API. If the user explicitly declines, inline values are allowed.

Non-sensitive values (non-secret header names, environment labels) can be passed inline.

### Shared Credentials Across Multiple Targets

When configuring multiple targets that use **the same credentials**, the credential may already exist in the credential manager from a previous target. Since sensitive (obfuscated) values cannot be read back, the agent cannot verify whether it matches — this causes a new credential entry per target, polluting the credential manager.

**Rule:** When multiple targets share the same credential and it already exists with `is_sensitive=True`, **prompt the user** to deobfuscate it (update to `is_sensitive=False` via `probely_update_credential`) so it can be read back and reused across targets. Inform the user why deobfuscation is needed.

**Workflow for shared credentials:**
1. Create the credential normally with `is_sensitive=True` for the first target.
2. When a subsequent target needs the same credential, find the existing one via `probely_list_credentials`.
3. If the existing credential is sensitive (is_sensitive=true), prompt the user: *"The credential '<name>' is obfuscated. To reuse it across multiple targets, it needs to be deobfuscated. Would you like to proceed?"*
4. If the user agrees, update it: `probely_update_credential(credentialId, is_sensitive=False)`.
5. Reuse the same credential `uri` for the new target.

**Pattern:**
```
cred = probely_create_credential(
  name="<target_name> - <description>",   # e.g. "MyAPI - Bearer token"
  value="the_actual_secret_value",
  is_sensitive=True                       # always sensitive by default
)
# cred["uri"] → "credentials://xxxx"
```

**Credential URIs:** Use the format `credentials://<credential_id>` (e.g., `credentials://4DY4qGohso1r`).
Get credential URIs from `probely_list_credentials` or `probely_create_credential`.
**Do NOT use template syntax like `{{cred-name}}`.**

## API Onboarding Workflow

When the user wants to scan an **API**, follow this workflow:

**Target name:** Use the name the user provides. **If the user does not specify a name**, use the API name derived from the schema title, Postman collection name, or the domain. Example: no name given for https://api.example.com → **Example API**. A default label (e.g. "Agentic") is auto-applied from the MCP server config — **do NOT look up, create, or pass labels manually** unless the user explicitly asks for additional labels.

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
Validate the schema file before uploading it. If the schema has violations fix them first. 
```
probely_create_api_target_from_openapi(
  name: "API Name",
  target_url: "https://api.example.com",
  openapi_schema_url: "https://..." OR openapi_schema_json: {...},
  desc: "Description",
  labels: ["api", "project-name"]
)
```

### Troubleshooting Target Creation

When creating a target, the API may return warnings. Handle them as follows:

- **"Target already exists"** — The Probely API warns when a target with the same URL already exists. **Do NOT treat this as an error.** Inform the user that a target with this URL already exists and ask whether they want to proceed with creating a duplicate or use the existing target instead. If they choose to create a duplicate, use the `allow_duplicate=True` parameter. If they choose the existing one, use `probely_list_targets(search="<url>")` to find it.
- **"Target didn't match server URL from API schema"** — This warning appears when the `target_url` passed during creation doesn't match any `servers[].url` entry in the OpenAPI schema. **Do NOT treat this as an error.** Inform the user about the mismatch and ask whether the target URL is correct. Common causes: the schema lists `http://localhost:3000` but the target URL is the production domain, or the schema has a different base path. The target is still created — the scanner will use the provided target URL.
- **Reachability errors** — If target creation fails because the target is unreachable or the domain cannot be resolved, ask the user whether you should retry with `skip_reachability_check=True`. Only retry after the user explicitly agrees.

#### Creating Duplicate Targets

To create a duplicate target (same URL as existing target), use `allow_duplicate=True`. This is useful when you want multiple targets for the same URL with different configurations (e.g., different authentication methods, different test scenarios):

```python
# For OpenAPI targets:
probely_create_api_target_from_openapi(
  name="MyAPI - Different Auth Method",
  target_url="https://api.example.com",  # Same URL as existing target
  openapi_schema_url="https://...",
  allow_duplicate=True  # Bypass duplicate URL check
)

# For Postman targets:
probely_create_api_target_from_postman(
  name="MyAPI - Test Scenario 2",
  target_url="https://api.example.com",  # Same URL as existing target
  postman_collection_url="https://...",
  allow_duplicate=True  # Bypass duplicate URL check
)
```

### Step 3: Configure API Authentication (if needed)

If the API requires authentication:
- Ask user for auth type (API key/Bearer token in headers, session cookies, or HTTP Basic Auth)
- By default, store sensitive values via `probely_create_credential` and use the credential URI in the header/cookie value. If the user explicitly declines, inline values are allowed.
- Use `probely_update_target` with the `headers` and/or `cookies` parameters

**IMPORTANT:** There are two different ways to configure headers/cookies in Probely:

1. **General custom headers/cookies** (via `probely_update_target` `headers`/`cookies` parameters): Sent with every scan request, NOT used for authentication. Simple structure: `{"name": "...", "value": "..."}`

2. **API authentication headers/cookies** (via `probely_update_target` `api_auth_headers`/`api_auth_cookies` parameters): Used for authentication. Requires full structure with authentication flags. The tool automatically configures `api_scan_settings`.

#### Authentication Method 1: HTTP Basic Auth

Use `probely_update_target` with `basic_auth_username` and `basic_auth_password` parameters:

```
# When user opts in to credentials management:
username_cred = probely_create_credential(name="<target_name> - username", value="api-user", is_sensitive=False)
password_cred = probely_create_credential(name="<target_name> - password", value="secret123", is_sensitive=True)

probely_update_target(
  targetId=targetId,
  basic_auth_username=username_cred["uri"],  # e.g., "credentials://4DY4qGohso1r"
  basic_auth_password=password_cred["uri"]   # e.g., "credentials://3B7JRXx6vbrD"
)

# When user does NOT opt in:
probely_update_target(
  targetId=targetId,
  basic_auth_username="api-user",
  basic_auth_password="secret123"
)
```

#### Authentication Method 2: Static Headers/Cookies (API Keys, Bearer Tokens, Session Cookies)

Use `probely_update_target` with `api_auth_headers` and/or `api_auth_cookies` parameters:

```
# Example 1: API Key Header Authentication
# When user opts in to credentials management:
api_key_cred = probely_create_credential(name="<target_name> - API key", value="sk-live-xxx", is_sensitive=True)

probely_update_target(
  targetId=targetId,
  api_auth_headers=[{
    "name": "X-API-Key",
    "value": api_key_cred["uri"],  # e.g., "credentials://3hBVSPfBbcaH"
    "value_is_sensitive": False,
    "allow_testing": False,
    "authentication": True,
    "authentication_secondary": False
  }]
)

# When user does NOT opt in:
probely_update_target(
  targetId=targetId,
  api_auth_headers=[{
    "name": "X-API-Key",
    "value": "sk-live-xxx",  # Inline value
    "value_is_sensitive": False,
    "allow_testing": False,
    "authentication": True,
    "authentication_secondary": False
  }]
)

# Example 2: Bearer Token Authentication
token_cred = probely_create_credential(name="<target_name> - Bearer token", value="eyJhb...", is_sensitive=True)

probely_update_target(
  targetId=targetId,
  api_auth_headers=[{
    "name": "Authorization",
    "value": f"Bearer {token_cred['uri']}",  # Note: prefix with "Bearer "
    "value_is_sensitive": False,
    "allow_testing": False,
    "authentication": True,
    "authentication_secondary": False
  }]
)

# Example 3: Session Cookie Authentication
cookie_cred = probely_create_credential(name="<target_name> - session cookie", value="secret-token", is_sensitive=True)

probely_update_target(
  targetId=targetId,
  api_auth_cookies=[{
    "name": "session",
    "value": cookie_cred["uri"],  # e.g., "credentials://32otBAEip2Km"
    "value_is_sensitive": False,
    "allow_testing": False,
    "authentication": True,
    "authentication_secondary": False
  }]
)

# Example 4: Combined Headers and Cookies
probely_update_target(
  targetId=targetId,
  api_auth_headers=[{
    "name": "X-Secret-Header",
    "value": "credentials://xxx",
    "value_is_sensitive": False,
    "allow_testing": False,
    "authentication": True,
    "authentication_secondary": False
  }],
  api_auth_cookies=[{
    "name": "secret-cookie",
    "value": "credentials://yyy",
    "value_is_sensitive": False,
    "allow_testing": False,
    "authentication": True,
    "authentication_secondary": False
  }]
)
```

**Note:** The `probely_update_target` tool automatically sets `api_scan_settings` with:
- `api_login_enabled: True`
- `api_login_method: "headers_or_cookies"`
- `api_headers_cookies_login_enabled_secondary: False`

