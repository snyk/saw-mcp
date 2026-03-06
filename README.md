# Snyk API&Web (SAW) MCP Server

An MCP server (FastMCP 2.0) that exposes the Snyk API&Web API as MCP tools, covering: Targets, Scans, Findings, Login Sequences, Authentication, Logout Detection, Extra Hosts, Labels, Teams, Users, Scanning Agents, Target Settings, and Reports. It can also create API targets from OpenAPI schemas or Postman collections.

## Features
- Full coverage via dedicated tools plus a generic `probely_request` for any API path
- Uses Snyk API&Web API key from config only (no hardcoding)
- Easy setup with Python venv
- Simple packaging to `.tgz` for distribution
- IDE-friendly (Cursor, Devin, etc.)

## Requirements
- Python 3.10+
- Internet access to reach the Snyk API&Web API

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Edit `config/config.yaml` and set your Snyk API&Web API key:
```yaml
saw:
  base_url: "https://api.probely.com"
  api_key: "YOUR_SAW_API_KEY"
```

## Run the server
```bash
./venv/bin/python -m snyk_apiweb.server
```

## Cursor IDE integration
1. Open Settings → Features → Model Context Protocol (MCP)
2. Add a new MCP server:
   - Name: `SAW` (or `Snyk API&Web`)
   - Command: `./venv/bin/python`
   - Args: `-m`, `snyk_apiweb.server`
   - Env: `MCP_SAW_CONFIG_PATH=./config/config.yaml`
3. Save and restart Cursor.

### Cursor mcp.json example

```json
{
  "mcpServers": {
    "SAW": {
      "command": "/<basedir>/saw-mcpserver/venv/bin/python",
      "args": ["-m", "snyk_apiweb.server"],
      "env": {
        "PYTHONPATH": "/<basedir>/saw-mcpserver",
        "MCP_SAW_CONFIG_PATH": "/<basedir>/saw-mcpserver/config/config.yaml"
      }
    }
}
```

Note: If your IDE does not resolve relative paths from the project root, use absolute paths for `command` and set `PYTHONPATH` to the project directory.

## Devin and other IDEs
Configure a custom MCP server with the same command and arguments above. Ensure the environment variable `MCP_SAW_CONFIG_PATH` points to your `config.yaml`.

## Installing Skills and Rules

The SAW MCP server ships with **project rules** and **agent skills** that teach the AI how to use the tools effectively. These must be linked into the correct locations so Cursor can find them.

### Project Rules

The rules file tells the AI to use SAW MCP tools for any Snyk API&Web task. Hard-link it into each project where you want SAW integration:

```bash
# From your project root
mkdir -p .cursor/rules
ln /<basedir>/saw-mcpserver/config/saw_rules.mdc .cursor/rules/saw_rules.mdc
```

### Agent Skills

Skills provide step-by-step workflows for target onboarding (web apps, APIs). Hard-link the skill files into your global Cursor skills folder:

```bash
# Create the global skills directories
mkdir -p ~/.cursor/skills/saw-web-target-configuration
mkdir -p ~/.cursor/skills/saw-api-target-configuration

# Hard-link each skill file
ln /<basedir>/saw-mcpserver/config/skills/saw-web-target-configuration/SKILL.md ~/.cursor/skills/saw-web-target-configuration/SKILL.md
ln /<basedir>/saw-mcpserver/config/skills/saw-api-target-configuration/SKILL.md ~/.cursor/skills/saw-api-target-configuration/SKILL.md
```

> **Why hard links?** Hard links keep a single source of truth in the MCP server repo. When skills or rules are updated (e.g. via `git pull`), every project picks up the changes automatically — no need to copy files again. Hard links are preferred over symlinks because some tools and editors don't follow symbolic links correctly.

### Available skills

| Skill | Path | Description |
|-------|------|-------------|
| Web Target Configuration | `config/skills/saw-web-target-configuration/` | Configure web app targets with login sequences, 2FA, logout detection, and extra host detection |
| API Target Configuration | `config/skills/saw-api-target-configuration/` | Configure API targets from OpenAPI/Swagger schemas or Postman collections |

### Key rules include
- Always use SAW MCP tools for any Snyk API&Web / SAW / Probely task
- API onboarding: Obtain OpenAPI/Postman schema, create API target
- Webapp onboarding: Record login sequence with Playwright, configure auth
- Vulnerability remediation workflow
- Active scan monitoring

## Packaging
Create a distributable tarball:
```bash
bash scripts/package.sh
```
This produces `dist/SnykAPIWeb.tgz` with the full project and install instructions.

## Security Best Practices
- On loading a new project, match it to an existing target in Snyk API&Web (via `probely_list_targets`).
- If vulnerabilities exist, use findings tools to prioritize fixes.

## API key storage (recommended practice)
- Store the Snyk API&Web API key only in the server config file: `config/config.yaml` (field `saw.api_key` or `probely.api_key`).
- Do not place the API key in `~/.cursor/mcp.json`. Keep secrets out of IDE-global config.
- Keep `config/config.yaml` out of version control and restrict file permissions (e.g., `chmod 600 config/config.yaml`).
- Optionally move the config file to a secure location and set `MCP_SAW_CONFIG_PATH` to that path.

## Tool Filtering

You can enable or disable specific tools in `config/config.yaml`:

### Whitelist Mode (only enable specific tools)
```yaml
tools:
  enabled:
    - probely_list_targets
    - probely_create_target
    - probely_start_scan
    - probely_list_findings
    - probely_configure_form_login
    - probely_configure_2fa
```

### Blacklist Mode (disable specific tools)
```yaml
tools:
  disabled:
    - probely_delete_target
    - probely_delete_user
    - probely_request  # Disable raw API access
```

If `enabled` is set, it takes precedence (whitelist mode). If neither is set, all tools are available.

## Tools Overview (selection)
- `probely_list_targets(search?)`, `probely_create_target(name, url, ...)`, `probely_start_scan(targetId, profile?)` 
- `probely_list_findings(targetId, severity?, state?)`, `probely_update_finding(targetId, findingId, state)`
- `probely_create_scan_report(scanId, format?)`, `probely_download_report(reportId)`
- `probely_create_sequence(targetId, name, content, ...)`, `probely_configure_sequence_login(targetId, enabled)`
- `probely_configure_form_login(targetId, login_url, username_field, password_field, username, password)`
- `probely_configure_2fa(targetId, otp_secret, otp_placeholder?, ...)`
- `probely_create_api_target_from_postman(name, target_url, postman_collection_url|postman_collection_json, ...)`
- `probely_create_api_target_from_openapi(name, target_url, openapi_schema_url|openapi_schema_json, ...)`
- `probely_request(method, path, params?, json?, data?)` for any endpoint
