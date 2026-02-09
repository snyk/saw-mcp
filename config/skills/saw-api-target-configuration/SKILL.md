---
name: saw-api-target-configuration
description: Configure Snyk API&Web API targets from OpenAPI/Swagger schemas or Postman collections. Use when creating API targets for security scanning.
---

# SAW API Target Configuration Skill

Configure API targets for Snyk API&Web (SAW/Probely) security scanning. For web application targets with authentication, use the `saw-web-target-configuration` skill instead.

When you finish adding/configuring a target, always summarize it with a table, and include a link to the target on SAW. Use the SAW app URL **https://plus.probely.app**. Include a column if you added extra hosts or not and in case you did, which ones.

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

## Available MCP Tools Reference

### Target Management
- `probely_list_targets(search?)` - List all targets
- `probely_get_target(targetId)` - Get target details
- `probely_create_target(name, url, desc?, label_ids?)` - Create new target
- `probely_update_target(targetId, name?, url?, desc?, label_ids?)` - Update target
- `probely_delete_target(targetId)` - Delete target

### API Target Creation
- `probely_create_api_target_from_postman(...)` - Create from Postman
- `probely_create_api_target_from_openapi(...)` - Create from OpenAPI

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
