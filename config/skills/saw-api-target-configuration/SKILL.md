---
name: saw-api-target-configuration
description: Configure Snyk API&Web API targets from OpenAPI/Swagger schemas or Postman collections. Use when creating API targets for security scanning.
---

# SAW API Target Configuration Skill

Configure API targets for Snyk API&Web (SAW/Probely) security scanning. For web application targets with authentication, use the `saw-web-target-configuration` skill instead.

When you finish adding/configuring a target, always summarize it with a table, and include a link to the target on SAW. Use the SAW app URL **https://plus.probely.app**. Include a column if you added extra hosts or not and in case you did, which ones.

## API Onboarding Workflow

When the user wants to scan an **API**, follow this workflow:

**Target name:** Use the name the user provides. **If the user does not specify a name**, use **Agentic - &lt;API name&gt;** where the API name is derived from the schema title, Postman collection name, or the domain. Example: no name given for https://api.example.com → **Agentic - Example API**.

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

