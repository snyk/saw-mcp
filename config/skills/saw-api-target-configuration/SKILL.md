---
name: saw-api-target-configuration
description: Configure Snyk API&Web API targets from OpenAPI/Swagger schemas or Postman collections. Use when creating API targets for security scanning.
---

# SAW API Target Configuration Skill

Configure API targets for Snyk API&Web (SAW/Probely) security scanning. For web application targets with authentication, use the `saw-web-target-configuration` skill instead.

When you finish adding/configuring a target, always summarize it with a table, and include a link to the target on SAW. Use the SAW app URL **https://plus.probely.app**. Include a column if you added extra hosts or not and in case you did, which ones.

## Credentials Management — ALWAYS Use for Sensitive Values

**NEVER pass sensitive values inline.** Always store them via `probely_create_credential` first and use the returned `uri` (e.g. `credentials://xxxx`) wherever the API accepts a value.

This applies to:
- **Custom headers** with sensitive values (API keys, Bearer tokens, auth tokens)
- **Custom cookies** with sensitive values (session tokens, secrets)
- **Basic Auth credentials** — store the password via credential manager

**Pattern:**
```
cred = probely_create_credential(
  name="<target_name> - <description>",   # e.g. "MyAPI - Bearer token"
  value="the_actual_secret_value",
  is_sensitive=True
)
# cred["uri"] → "credentials://xxxx" — use this wherever the secret is needed
```

Non-sensitive values (non-secret header names, environment labels) can be passed inline.

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

### Step 3: Configure API Authentication (if needed)

If the API requires authentication:
- Ask user for auth type (API key, Bearer token, OAuth, Basic Auth)
- **Store all sensitive values via credential manager first**, then use the credential URI in the header/cookie value
- Use `probely_update_target` with the `headers` and/or `cookies` parameters

**Examples:**

```
# Bearer token
token_cred = probely_create_credential(name="<target_name> - Bearer token", value="eyJhb...", is_sensitive=True)
probely_update_target(targetId, headers=[{"name": "Authorization", "value": token_cred["uri"]}])

# API key header
key_cred = probely_create_credential(name="<target_name> - API key", value="sk-live-xxx", is_sensitive=True)
probely_update_target(targetId, headers=[{"name": "X-Api-Key", "value": key_cred["uri"]}])

# Basic Auth (store the password, pass username inline)
pwd_cred = probely_create_credential(name="<target_name> - Basic Auth password", value="secret", is_sensitive=True)
probely_update_target(targetId, headers=[{"name": "Authorization", "value": pwd_cred["uri"]}])

# Custom cookies with sensitive values
cookie_cred = probely_create_credential(name="<target_name> - session cookie", value="secret-token", is_sensitive=True)
probely_update_target(targetId, cookies=[{"name": "session", "value": cookie_cred["uri"]}])
```

