# SAW MCP Server — AppBuilder Specification

> **Purpose:** This document is a complete technical specification for rebuilding the Snyk API&Web (SAW) MCP Server from scratch. It covers architecture, every source file, every MCP tool, the HTTP client, configuration system, skills, rules, scripts, and deployment. An AI agent given this document should be able to reproduce the entire project.

---

## Table of Contents

1. [Project Identity](#1-project-identity)
2. [Architecture Overview](#2-architecture-overview)
3. [File Tree](#3-file-tree)
4. [Dependencies](#4-dependencies)
5. [Configuration System](#5-configuration-system)
6. [Source Code — Module by Module](#6-source-code--module-by-module)
   - 6.1 [Package Init](#61-package-init)
   - 6.2 [Config Loader (`config.py`)](#62-config-loader-configpy)
   - 6.3 [HTTP Client (`probely_client.py`)](#63-http-client-probely_clientpy)
   - 6.4 [MCP Tools (`tools.py`)](#64-mcp-tools-toolspy)
   - 6.5 [Server Entry Point (`server.py`)](#65-server-entry-point-serverpy)
7. [Complete MCP Tool Catalog](#7-complete-mcp-tool-catalog)
8. [API Endpoint Map](#8-api-endpoint-map)
9. [Key Implementation Details](#9-key-implementation-details)
10. [Skills](#10-skills)
11. [Rules](#11-rules)
12. [Scripts & Packaging](#12-scripts--packaging)
13. [IDE Integration](#13-ide-integration)
14. [Security Practices](#14-security-practices)
15. [Gitignore](#15-gitignore)

---

## 1. Project Identity

| Field | Value |
|-------|-------|
| **Name** | Snyk API&Web MCP Server (SAW) |
| **Legacy name** | Probely MCP Server |
| **Language** | Python 3.10+ |
| **MCP framework** | FastMCP 2.0 (STDIO transport) |
| **Upstream API** | Snyk API&Web (Probely) — `https://api.probely.com` |
| **Auth scheme** | JWT bearer token (`Authorization: JWT <api_key>`) |
| **License** | MIT |
| **Package name** | `snyk_apiweb` |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  AI IDE (Cursor / Devin / Windsurf / etc.)      │
│  ┌───────────────────────────────────────┐      │
│  │  MCP Client                           │      │
│  └───────────────┬───────────────────────┘      │
└──────────────────┼──────────────────────────────┘
                   │  STDIO (JSON-RPC)
┌──────────────────┼──────────────────────────────┐
│  SAW MCP Server  │                              │
│  ┌───────────────┴───────────────────────┐      │
│  │  FastMCP 2.0 app  (tools.py)          │      │
│  │  46 registered tool functions          │      │
│  └───────────────┬───────────────────────┘      │
│                  │                               │
│  ┌───────────────┴───────────────────────┐      │
│  │  ProbelyClient  (probely_client.py)   │      │
│  │  requests.Session + tenacity retries  │      │
│  └───────────────┬───────────────────────┘      │
│                  │                               │
│  ┌───────────────┴───────────────────────┐      │
│  │  Config loader  (config.py)           │      │
│  │  YAML → base_url, api_key, filters    │      │
│  └───────────────────────────────────────┘      │
└─────────────────────────────────────────────────┘
                   │  HTTPS
                   ▼
        ┌─────────────────────┐
        │  api.probely.com    │
        │  (Snyk API&Web API) │
        └─────────────────────┘
```

**Data flow:** IDE → (STDIO) → FastMCP app → tool function → ProbelyClient method → HTTP request → Probely API → JSON response → back up the chain.

---

## 3. File Tree

```
saw-mcpserver/
├── snyk_apiweb/                          # Python package (the server)
│   ├── __init__.py                       # Exports: config, probely_client, tools, server
│   ├── config.py                         # YAML config loader + helpers
│   ├── probely_client.py                 # HTTP REST client for Probely API
│   ├── server.py                         # Entry point: main() → build_server().run()
│   └── tools.py                          # All MCP tool definitions + build_server()
│
├── config/                               # Configuration
│   ├── config.yaml                       # Runtime config (gitignored — contains real API key)
│   ├── config.yaml.dist                  # Template config (committed — API key = "CHANGEME")
│   ├── saw_rules.mdc                     # Cursor rules file (hard-linked into projects)
│   └── skills/                           # Agent skills
│       ├── saw-api-target-configuration/
│       │   └── SKILL.md                  # API target onboarding workflow
│       └── saw-web-target-configuration/
│           └── SKILL.md                  # Web target onboarding workflow (413 lines)
│
├── scripts/
│   ├── dev.sh                            # Start in FastMCP dev mode (hot-reload)
│   ├── inspector.sh                      # Start MCP Inspector (web UI for testing tools)
│   └── package.sh                        # Build dist/SnykAPIWeb-<version>.tgz (redacts API key)
│
├── .cursor/
│   └── rules/
│       └── snyk_rules.mdc               # Auto-generated by Snyk Security extension (gitignored)
│
├── .vscode/
│   └── settings.json                     # {"snyk.advanced.autoSelectOrganization": true}
│
├── .gitignore
├── USER_GUIDE.md                         # User guide: usage, examples, tool reference
├── LICENSE                               # MIT
├── README.md                             # Full documentation
└── requirements.txt                      # Python dependencies
```

---

## 4. Dependencies

**`requirements.txt`:**

```
fastmcp>=2.0.0
requests>=2.32.3
pydantic>=2.8.2
PyYAML>=6.0.2
typer>=0.12.5
tenacity>=8.5.0
```

| Package | Purpose |
|---------|---------|
| `fastmcp` | MCP server framework (tool registration, STDIO transport, JSON-RPC) |
| `requests` | HTTP client for Probely API calls |
| `pydantic` | Schema validation (used internally by FastMCP for tool parameter schemas) |
| `PyYAML` | Parse `config.yaml` |
| `typer` | CLI framework (used internally by FastMCP) |
| `tenacity` | Retry logic with exponential backoff for transient HTTP errors |

---

## 5. Configuration System

### 5.1 Config File Format (`config/config.yaml.dist`)

```yaml
# Snyk API&Web (SAW) MCP Server Configuration
saw:
  base_url: "https://api.probely.com"
  api_key: "CHANGEME"

server:
  name: "Snyk API&Web"

target_defaults:
  label: "Agentic"          # Auto-applied label for new targets (created if missing)
  # name_prefix: "Agentic - "  # Prepended to every target name

tools:
  # Whitelist mode (takes precedence):
  # enabled:
  #   - probely_list_targets
  #   - probely_create_target

  # Blacklist mode:
  disabled:
    - probely_delete_sequence
    - probely_delete_extra_host
    - probely_request
```

### 5.2 Config Resolution

The config path is resolved in this priority:
1. Explicit `path` argument to `load_config()`
2. Environment variable `MCP_SAW_CONFIG_PATH`
3. Environment variable `MCP_PROBELY_CONFIG_PATH` (legacy)
4. Default: `<project_root>/config/config.yaml`

### 5.3 Legacy Support

The config module supports both `saw` and `probely` YAML section names. The `saw` section takes priority; `probely` is the fallback. API key values `"REPLACE_WITH_YOUR_SAW_API_KEY"` and `"REPLACE_WITH_YOUR_PROBELY_API_KEY"` are treated as unset and raise a `RuntimeError`.

### 5.4 Config Helpers (all in `config.py`)

| Function | Returns | Description |
|----------|---------|-------------|
| `load_config(path?)` | `Dict[str, Any]` | Load and parse the YAML config file |
| `get_probely_base_url(cfg)` | `str` | Extract base URL, strip trailing slash |
| `get_probely_api_key(cfg)` | `str` | Extract API key, raise if placeholder |
| `get_target_defaults(cfg)` | `Dict` with `default_label` and `name_prefix` | Target creation defaults |
| `get_tool_filter(cfg)` | `Dict` with `enabled_tools` and `disabled_tools` | Tool whitelist/blacklist |
| `is_tool_enabled(name, filter)` | `bool` | Check if a tool passes the filter |

---

## 6. Source Code — Module by Module

### 6.1 Package Init

**`snyk_apiweb/__init__.py`**

```python
__all__ = ["config", "probely_client", "tools", "server"]
```

### 6.2 Config Loader (`config.py`)

Implements the configuration system described in Section 5. Key design decisions:
- Uses `os.path.dirname(__file__)` twice to locate the project root for the default config path.
- Both `saw.*` and `probely.*` config sections are supported for backward compatibility.
- Tool filtering supports whitelist (precedence) and blacklist modes.
- `get_target_defaults()` returns `default_label` as `{"name": "..."}` (ready for the Probely API which resolves labels by name).

### 6.3 HTTP Client (`probely_client.py`)

**Class: `ProbelyClient`**

#### Constructor

```python
ProbelyClient(base_url: str, api_key: str, timeout: int = 60)
```

- Creates a `requests.Session` with persistent headers:
  - `Authorization: JWT {api_key}`
  - `Accept: application/json`
- Strips trailing slash from `base_url`.

#### Core Request Method

```python
@retry(reraise=True, stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=1, max=8),
       retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)))
def request(self, method, path, params?, json?, data?, files?, headers?) -> Tuple[int, Dict[str, Any]]
```

- Retries up to 3 times on `ConnectionError` and `Timeout` with exponential backoff (1s → 2s → 4s, max 8s).
- Auto-prepends `/` to paths if missing.
- Parses JSON responses; wraps list responses in `{"results": [...]}`.
- Non-JSON responses are returned as `{"raw": "..."}`.
- On error (non-2xx), enriches the body with `status`, `reason`, and `url` under an `error` key.

#### Client Methods by Category

**Users:**
- `list_users(page?)` → `GET /users/`
- `get_user(user_id)` → `GET /users/{id}/`
- `create_user(email, name, role?)` → `POST /users/`
- `update_user(user_id, **fields)` → `PATCH /users/{id}/`
- `delete_user(user_id)` → `DELETE /users/{id}/`

**API Users:**
- `list_api_users(page?)` → `GET /api-users/`
- `get_api_user(api_user_id)` → `GET /api-users/{id}/`
- `create_api_user(name, permissions?)` → `POST /api-users/`
- `delete_api_user(api_user_id)` → `DELETE /api-users/{id}/`

**Account:**
- `get_account()` → `GET /account/`
- `update_account(**fields)` → `PATCH /account/`

**Roles & Permissions:**
- `list_roles(page?)` → `GET /roles/`
- `get_role(role_id)` → `GET /roles/{id}/`
- `list_permissions(page?)` → `GET /permissions/`

**Teams:**
- `list_teams(page?)` → `GET /teams/`
- `get_team(team_id)` → `GET /teams/{id}/`
- `create_team(name, description?)` → `POST /teams/`
- `update_team(team_id, **fields)` → `PATCH /teams/{id}/`
- `delete_team(team_id)` → `DELETE /teams/{id}/`

**Domains:**
- `list_domains(page?)` → `GET /domains/`
- `get_domain(domain_id)` → `GET /domains/{id}/`
- `create_domain(name)` → `POST /domains/`
- `verify_domain(domain_id)` → `POST /domains/{id}/verify/`
- `delete_domain(domain_id)` → `DELETE /domains/{id}/`

**Labels:**
- `list_labels(page?)` → `GET /labels/`
- `get_label(label_id)` → `GET /labels/{id}/`
- `create_label(name, color?)` → `POST /labels/`
- `update_label(label_id, **fields)` → `PATCH /labels/{id}/`
- `delete_label(label_id)` → `DELETE /labels/{id}/`
- `resolve_labels(label_names)` → converts `["Name"]` to `[{"name": "Name"}]`

**Targets:**
- `list_targets(page?, search?)` → `GET /targets/`
- `get_target(target_id)` → `GET /targets/{id}/`
- `create_target(name, url, desc?, label_names?, default_label?, name_prefix?, scanning_agent_id?)` → `POST /targets/`
  - Nests `name`, `url`, `desc` under `site` key.
  - Merges config default label + user labels, deduplicated by name.
  - Prepends `name_prefix` to target name.
  - Optionally sets `scanning_agent: {"id": "..."}`.
- `update_target(target_id, **fields)` → `PATCH /targets/{id}/`
- `delete_target(target_id)` → `DELETE /targets/{id}/`
- `verify_target(target_id)` → `POST /targets/{id}/verify/`

**Login Sequences:**
- `list_sequences(target_id, page?)` → `GET /targets/{id}/sequences/`
- `get_sequence(target_id, sequence_id)` → `GET /targets/{id}/sequences/{sid}/`
- `create_sequence(target_id, name, sequence_type, content, enabled?, custom_field_mappings?)` → `POST /targets/{id}/sequences/`
  - Pretty-prints JSON content via `_pretty_json_content()`.
- `update_sequence(target_id, sequence_id, **fields)` → `PATCH /targets/{id}/sequences/{sid}/`
- `delete_sequence(target_id, sequence_id)` → `DELETE /targets/{id}/sequences/{sid}/`

**Authentication Configuration (via target PATCH):**
- `configure_form_login(target_id, login_url, username_field, password_field, username, password, check_pattern?)` → `PATCH /targets/{id}/`
  - Sets `has_form_login: True`, `has_sequence_login: False`, `auth_enabled: True` under `site`.
  - `form_login` is an array of `{name, value}` field mappings.
- `configure_sequence_login(target_id, enabled?)` → `PATCH /targets/{id}/`
  - Mutually exclusive with form login (auto-disables form login when enabling sequence login).
- `configure_2fa(target_id, otp_secret, otp_placeholder?, otp_algorithm?, otp_digits?, otp_type?)` → `PATCH /targets/{id}/`
  - Sets `has_otp: True` and OTP config fields under `site`.
- `disable_2fa(target_id)` → `PATCH /targets/{id}/`

**Logout Detection:**
- `list_logout_detectors(target_id)` → `GET /targets/{id}/logout/`
- `create_logout_detector(target_id, detector_type, value)` → `POST /targets/{id}/logout/`
  - `detector_type`: `"text"`, `"url"`, or `"sel"` (CSS selector)
- `configure_logout_detection(target_id, enabled?, check_session_url?, logout_detector_type?, logout_detector_value?, logout_condition?)` → multi-step:
  1. Sets `check_session_url` via `PATCH /targets/{id}/`.
  2. Checks for existing detectors; creates one if none exist.
  3. Auto-detects CSS selector from login sequence via `_find_login_sequence_selector()` if no detector type/value provided.
  4. Falls back to `text: "Login"` if no login sequence found.
  5. Enables `logout_detection_enabled: True` via `PATCH /targets/{id}/`.
  - `logout_condition`: `"any"` (OR, default) or `"all"` (AND).
- `_find_login_sequence_selector(target_id)` → private method
  - Reads enabled login sequences, parses JSON content, finds first `fill_value` step with a `css` field.

**Extra Hosts (API path uses `/assets/`):**
- `list_extra_hosts(target_id, page?)` → `GET /targets/{id}/assets/`
- `get_extra_host(target_id, extra_host_id)` → `GET /targets/{id}/assets/{eid}/`
- `create_extra_host(target_id, hostname, ip_address?)` → `POST /targets/{id}/assets/`
  - Maps `hostname` to both `host` and `name` fields.
  - Sets `ip_address` in `desc` field.
  - Uses `skip_reachability_check=true` query param.
- `update_extra_host(target_id, extra_host_id, **fields)` → `PATCH /targets/{id}/assets/{eid}/`
  - Maps `hostname` to `host` for the API.
- `delete_extra_host(target_id, extra_host_id)` → `DELETE /targets/{id}/assets/{eid}/`

**Scans:**
- `list_scans(target_id, page?)` → `GET /targets/{id}/scans/`
- `get_scan(target_id, scan_id)` → `GET /targets/{id}/scans/{sid}/`
- `start_scan(target_id, profile?)` → `POST /targets/{id}/scan_now/` (note: `scan_now`, not `scans`)
- `stop_scan(target_id, scan_id)` → `POST /targets/{id}/scans/{sid}/stop/`
- `cancel_scan(target_id, scan_id)` → `POST /targets/{id}/scans/{sid}/cancel/`

**Findings:**
- `list_findings(target_id, page?, severity?, state?)` → `GET /targets/{id}/findings/`
- `get_finding(target_id, finding_id)` → `GET /targets/{id}/findings/{fid}/`
- `update_finding(target_id, finding_id, state?)` → `PATCH /targets/{id}/findings/{fid}/`
- `bulk_update_findings(target_id, finding_ids, state?)` → `POST /targets/{id}/findings/bulk-update/`

**Target Settings:**
- `get_target_settings(target_id)` → `GET /targets/{id}/settings/`
- `update_target_settings(target_id, **fields)` → `PATCH /targets/{id}/settings/`

**Reports (top-level endpoint, not under targets):**
- `create_scan_report(scan_id, report_type?, report_format?)` → `POST /report/`
  - `report_type`: `"default"`, `"executive"`, `"owasp"`, `"pci"`, `"hipaa"`, `"iso27001"`
  - `report_format`: `"pdf"` or `"html"`
- `download_report(report_id)` → `GET /report/{id}/download/`
- `get_report(report_id)` → `GET /report/{id}/`

**Integrations:**
- `list_integrations()` → `GET /integrations/`
- `get_integration(integration_id)` → `GET /integrations/{id}/`

**Scanning Agents:**
- `list_scanning_agents(page?, length?, status?, search?)` → `GET /scanning-agents/`
  - `status`: `"connected"`, `"connected_with_issues"`, `"disconnected"`
- `get_scanning_agent(agent_id)` → `GET /scanning-agents/{id}/`

**API Target Creation (multi-step, best-effort endpoint discovery):**
- `create_api_target_from_postman(name, target_url, postman_json, desc?, label_names?, default_label?, name_prefix?)`:
  1. Creates a target via `create_target()`.
  2. Tries POST to multiple candidate endpoints in order:
     - `/targets/{id}/apis/import/postman/`
     - `/targets/{id}/apis/import/`
     - `/targets/{id}/api/import/`
  3. Returns `target_id` + import result or error.

- `create_api_target_from_openapi(name, target_url, openapi_schema, desc?, label_names?, default_label?, name_prefix?)`:
  1. Creates a target via `create_target()`.
  2. Tries POST to multiple candidate endpoints in order:
     - `/targets/{id}/apis/import/openapi/`
     - `/targets/{id}/apis/import/swagger/`
     - `/targets/{id}/apis/import/`
     - `/targets/{id}/api/import/openapi/`
  3. Returns `target_id` + import result or error.

**Generic Fallback:**
- `raw(method, path, params?, json?, data?)` → proxies to `request()`, returns body only.

### 6.4 MCP Tools (`tools.py`)

#### `build_server()` Function

This is the central factory that:
1. Loads config via `load_config()`.
2. Extracts base URL, API key, tool filter, target defaults.
3. Creates `ProbelyClient(base_url, api_key)`.
4. Creates `FastMCP` app with server name from config.
5. Defines a `register_tool(name)` decorator that conditionally registers tools based on the tool filter.
6. Registers all tool functions.
7. Returns the `FastMCP` app instance.

#### Helper Functions

**`_parse_list_of_dicts(value)`** — Normalizes complex tool parameters:
- Handles native `list`, JSON string, Python-repr string (via `ast.literal_eval`), single `dict` → wraps in list.
- Needed because `from __future__ import annotations` + FastMCP/Pydantic can deliver complex types as strings.

**`_generate_totp(secret, algorithm?, digits?, period?)`** — Pure-Python TOTP implementation:
- Strips whitespace/dashes, uppercases, pads with `=` for base32.
- Uses HMAC-SHA1 (or configurable hash), 30-second period, 6 digits (configurable).
- Returns `{"code": "123456", "remaining_seconds": 17, "algorithm": "SHA1", "digits": 6}`.

#### Tool Registration Pattern

Each tool is defined as a nested function inside `build_server()` with closure access to `client` and `target_defaults`. The `@register_tool("probely_xxx")` decorator conditionally registers it:

```python
@register_tool("probely_tool_name")
def probely_tool_name(param1: str, param2: Optional[str] = None) -> Dict[str, Any]:
    """Docstring becomes the tool description in MCP."""
    return client.some_method(param1=param1, param2=param2)
```

If the tool is disabled by config, the function is returned without registration (undecorated).

### 6.5 Server Entry Point (`server.py`)

```python
from .tools import build_server

def main() -> None:
    app = build_server()
    app.run()

if __name__ == "__main__":
    main()
```

Run with: `python -m snyk_apiweb.server`

---

## 7. Complete MCP Tool Catalog

All tool names are prefixed with `probely_` for namespacing.

### Generic
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_request` | `method`, `path`, `params?`, `json?`, `data?` | Raw API request to any endpoint |

### User Management (read-only in tools layer)
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_get_user` | `userId` | Get user details |

### Teams
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_list_teams` | `page?` | List teams |
| `probely_get_team` | `teamId` | Get team details |

### Labels
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_create_label` | `name`, `color?` | Create a label |

### Targets
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_list_targets` | `page?`, `search?` | List/search targets |
| `probely_get_target` | `targetId` | Get target details |
| `probely_create_target` | `name`, `url`, `desc?`, `labels?`, `scanning_agent_id?` | Create a web target. Labels are name strings; default label auto-merged from config |
| `probely_update_target` | `targetId`, `name?`, `url?`, `desc?`, `labels?`, `scanning_agent_id?` | Update a target |
| `probely_delete_target` | `targetId` | Delete a target |

### Login Sequences
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_list_sequences` | `targetId`, `page?` | List login sequences |
| `probely_get_sequence` | `targetId`, `sequenceId` | Get sequence details |
| `probely_create_sequence` | `targetId`, `name`, `content`, `sequence_type?`, `enabled?`, `custom_field_mappings?` | Create login sequence (content = JSON string of steps) |
| `probely_update_sequence` | `targetId`, `sequenceId`, `name?`, `content?`, `enabled?`, `custom_field_mappings?` | Update login sequence |
| `probely_delete_sequence` | `targetId`, `sequenceId` | Delete login sequence |

### Authentication
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_configure_form_login` | `targetId`, `login_url`, `username_field`, `password_field`, `username`, `password`, `check_pattern?` | Configure form-based login (fallback for no Playwright) |
| `probely_configure_sequence_login` | `targetId`, `enabled?` | Enable/disable sequence login (mutually exclusive with form login) |
| `probely_configure_2fa_totp` | `targetId`, `otp_secret`, `otp_algorithm?`, `otp_digits?` | Configure TOTP 2FA. Auto-generates OTP code and returns it in `otp_code` field |
| `probely_disable_2fa` | `targetId` | Disable 2FA |
| `probely_generate_totp` | `secret`, `algorithm?`, `digits?`, `period?` | Generate a TOTP code from a seed (standalone, for use during Playwright recording) |

### Logout Detection
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_list_logout_detectors` | `targetId` | List logout detectors |
| `probely_create_logout_detector` | `targetId`, `detector_type`, `value` | Create logout detector (`text`/`url`/`sel`) |
| `probely_configure_logout_detection` | `targetId`, `enabled?`, `check_session_url?`, `logout_detector_type?`, `logout_detector_value?`, `logout_condition?` | Full logout detection setup (multi-step, auto-creates detector if needed) |

### Extra Hosts
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_list_extra_hosts` | `targetId`, `page?` | List extra hosts |
| `probely_get_extra_host` | `targetId`, `extraHostId` | Get extra host |
| `probely_create_extra_host` | `targetId`, `hostname`, `ip_address` | Add extra host |
| `probely_update_extra_host` | `targetId`, `extraHostId`, `hostname?`, `ip_address?` | Update extra host |
| `probely_delete_extra_host` | `targetId`, `extraHostId` | Delete extra host |

### Scans
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_list_scans` | `targetId`, `page?` | List scans |
| `probely_get_scan` | `targetId`, `scanId` | Get scan details/progress |
| `probely_start_scan` | `targetId`, `profile?` | Start a scan |
| `probely_stop_scan` | `targetId`, `scanId` | Stop a running scan |
| `probely_cancel_scan` | `targetId`, `scanId` | Cancel a scan |

### Findings
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_list_findings` | `targetId`, `page?`, `severity?`, `state?` | List findings with filters |
| `probely_get_finding` | `targetId`, `findingId` | Get finding details (description, CVSS, fix) |
| `probely_update_finding` | `targetId`, `findingId`, `state?` | Update finding state (`fixed`/`false_positive`/`accepted_risk`) |
| `probely_bulk_update_findings` | `targetId`, `findingIds`, `state?` | Bulk update finding states |

### Settings
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_get_target_settings` | `targetId` | Get target settings |
| `probely_update_target_settings` | `targetId`, `excluded_paths?`, `max_scan_duration?`, `scan_profile?` | Update target settings |

### Reports
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_create_scan_report` | `scanId`, `report_type?`, `format?` | Create report (types: default/executive/owasp/pci/hipaa/iso27001) |
| `probely_download_report` | `reportId` | Download report content |
| `probely_get_report` | `reportId` | Get report metadata/status |

### Scanning Agents
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_list_scanning_agents` | `page?`, `length?`, `status?`, `search?` | List scanning agents |
| `probely_get_scanning_agent` | `agentId` | Get scanning agent details |

### API Target Creation
| Tool | Parameters | Description |
|------|-----------|-------------|
| `probely_create_api_target_from_postman` | `name`, `target_url`, `postman_collection_url?`, `postman_collection_json?`, `desc?`, `labels?` | Create API target from Postman collection |
| `probely_create_api_target_from_openapi` | `name`, `target_url`, `openapi_schema_url?`, `openapi_schema_json?`, `desc?`, `labels?` | Create API target from OpenAPI/Swagger schema |

---

## 8. API Endpoint Map

All paths are relative to the base URL (`https://api.probely.com`). All paths end with `/`.

| HTTP Method | Path | Client Method |
|------------|------|---------------|
| GET | `/users/` | `list_users` |
| GET | `/users/{id}/` | `get_user` |
| POST | `/users/` | `create_user` |
| PATCH | `/users/{id}/` | `update_user` |
| DELETE | `/users/{id}/` | `delete_user` |
| GET | `/api-users/` | `list_api_users` |
| GET | `/api-users/{id}/` | `get_api_user` |
| POST | `/api-users/` | `create_api_user` |
| DELETE | `/api-users/{id}/` | `delete_api_user` |
| GET | `/account/` | `get_account` |
| PATCH | `/account/` | `update_account` |
| GET | `/roles/` | `list_roles` |
| GET | `/roles/{id}/` | `get_role` |
| GET | `/permissions/` | `list_permissions` |
| GET | `/teams/` | `list_teams` |
| GET | `/teams/{id}/` | `get_team` |
| POST | `/teams/` | `create_team` |
| PATCH | `/teams/{id}/` | `update_team` |
| DELETE | `/teams/{id}/` | `delete_team` |
| GET | `/domains/` | `list_domains` |
| GET | `/domains/{id}/` | `get_domain` |
| POST | `/domains/` | `create_domain` |
| POST | `/domains/{id}/verify/` | `verify_domain` |
| DELETE | `/domains/{id}/` | `delete_domain` |
| GET | `/labels/` | `list_labels` |
| GET | `/labels/{id}/` | `get_label` |
| POST | `/labels/` | `create_label` |
| PATCH | `/labels/{id}/` | `update_label` |
| DELETE | `/labels/{id}/` | `delete_label` |
| GET | `/targets/` | `list_targets` |
| GET | `/targets/{id}/` | `get_target` |
| POST | `/targets/` | `create_target` |
| PATCH | `/targets/{id}/` | `update_target`, `configure_form_login`, `configure_sequence_login`, `configure_2fa`, `disable_2fa`, `configure_logout_detection` |
| DELETE | `/targets/{id}/` | `delete_target` |
| POST | `/targets/{id}/verify/` | `verify_target` |
| GET | `/targets/{id}/sequences/` | `list_sequences` |
| GET | `/targets/{id}/sequences/{sid}/` | `get_sequence` |
| POST | `/targets/{id}/sequences/` | `create_sequence` |
| PATCH | `/targets/{id}/sequences/{sid}/` | `update_sequence` |
| DELETE | `/targets/{id}/sequences/{sid}/` | `delete_sequence` |
| GET | `/targets/{id}/logout/` | `list_logout_detectors` |
| POST | `/targets/{id}/logout/` | `create_logout_detector` |
| GET | `/targets/{id}/assets/` | `list_extra_hosts` |
| GET | `/targets/{id}/assets/{eid}/` | `get_extra_host` |
| POST | `/targets/{id}/assets/` | `create_extra_host` |
| PATCH | `/targets/{id}/assets/{eid}/` | `update_extra_host` |
| DELETE | `/targets/{id}/assets/{eid}/` | `delete_extra_host` |
| GET | `/targets/{id}/scans/` | `list_scans` |
| GET | `/targets/{id}/scans/{sid}/` | `get_scan` |
| POST | `/targets/{id}/scan_now/` | `start_scan` |
| POST | `/targets/{id}/scans/{sid}/stop/` | `stop_scan` |
| POST | `/targets/{id}/scans/{sid}/cancel/` | `cancel_scan` |
| GET | `/targets/{id}/findings/` | `list_findings` |
| GET | `/targets/{id}/findings/{fid}/` | `get_finding` |
| PATCH | `/targets/{id}/findings/{fid}/` | `update_finding` |
| POST | `/targets/{id}/findings/bulk-update/` | `bulk_update_findings` |
| GET | `/targets/{id}/settings/` | `get_target_settings` |
| PATCH | `/targets/{id}/settings/` | `update_target_settings` |
| POST | `/report/` | `create_scan_report` |
| GET | `/report/{id}/` | `get_report` |
| GET | `/report/{id}/download/` | `download_report` |
| GET | `/integrations/` | `list_integrations` |
| GET | `/integrations/{id}/` | `get_integration` |
| GET | `/scanning-agents/` | `list_scanning_agents` |
| GET | `/scanning-agents/{id}/` | `get_scanning_agent` |

---

## 9. Key Implementation Details

### 9.1 TOTP Generation

The server includes a pure-Python TOTP implementation (no external library like `pyotp`). This is used in two places:
1. **`probely_configure_2fa_totp`** — generates a TOTP code, configures 2FA on the target, and returns the code so it can be hardcoded in the login sequence.
2. **`probely_generate_totp`** — standalone tool for generating TOTP codes during Playwright-based login recording.

The implementation follows RFC 6238:
- Base32-decode the secret (with padding normalization).
- Compute HMAC with the counter (time / period).
- Dynamic truncation to extract the OTP digits.

### 9.2 Login Sequence Content

Login sequence `content` is a JSON string containing an array of step objects. The client pretty-prints this JSON before sending to the API (`_pretty_json_content()`). Sequence step types: `goto`, `click`, `dblclick`, `fill_value`, `fill_otp`, `change`, `press_key`, `mouseover`.

### 9.3 Custom Field Mappings

Credentials in login sequences use placeholder tokens (`[CUSTOM_USERNAME]`, `[CUSTOM_PASSWORD]`) rather than hardcoded values. The `custom_field_mappings` parameter maps these placeholders to actual values:

```json
[
  {"name": "[CUSTOM_USERNAME]", "value": "user@example.com", "value_is_sensitive": false, "enabled": true},
  {"name": "[CUSTOM_PASSWORD]", "value": "secret", "value_is_sensitive": true, "enabled": true}
]
```

The `_parse_list_of_dicts()` helper handles the fact that MCP frameworks sometimes deliver this as a JSON string instead of a native list.

### 9.4 Mutual Exclusivity of Auth Methods

The Probely API does not allow both form login and sequence login simultaneously. The client enforces this:
- `configure_form_login()` sets `has_form_login: True, has_sequence_login: False`.
- `configure_sequence_login(enabled=True)` sets `has_sequence_login: True, has_form_login: False`.

### 9.5 Logout Detection Auto-Configuration

`configure_logout_detection()` is the most complex client method. It performs multi-step API calls:
1. Sets the session check URL.
2. Checks for existing detectors; if none, auto-creates one by:
   - Using provided `logout_detector_type`/`value`, OR
   - Extracting a CSS selector from the login sequence's first `fill_value` step, OR
   - Falling back to `text: "Login"`.
3. Enables logout detection with optional `logout_condition` (`any`/`all`).

### 9.6 Extra Host API Mapping

The Probely API uses `/targets/{id}/assets/` for extra hosts, not a `/extra-hosts/` path. The `create_extra_host` method uses `skip_reachability_check=true` query parameter and maps `hostname` to both `host` and `name` fields.

### 9.7 Scan Start Endpoint

Starting a scan uses `POST /targets/{id}/scan_now/`, not `POST /targets/{id}/scans/`. This is specific to the Probely API.

### 9.8 Target Creation Payload Structure

The Probely API nests `name`, `url`, and `desc` under a `site` key, while `labels` and `scanning_agent` are top-level:

```json
{
  "site": {"name": "...", "url": "...", "desc": "..."},
  "labels": [{"name": "Agentic"}, {"name": "Production"}],
  "scanning_agent": {"id": "..."}
}
```

### 9.9 Label Resolution

Labels are passed by name. The Probely API resolves them server-side (reuses existing labels, creates missing ones). No client-side ID lookup is needed. The client's `resolve_labels()` simply converts `["Name"]` to `[{"name": "Name"}]`.

### 9.10 Tool Filtering

Tool registration is controlled by a decorator pattern. `register_tool(name)` checks `is_tool_enabled(name, tool_filter)` before calling `app.tool(name=name)`. If disabled, the function exists but is not registered with FastMCP.

### 9.11 API Target Import (Best-Effort Endpoint Discovery)

For Postman and OpenAPI import, the client tries multiple endpoint patterns since the exact path may vary by Probely account version. It iterates through candidates and returns the first successful response.

---

## 10. Skills

Skills are Cursor Agent Skills stored in `config/skills/` and hard-linked to `~/.cursor/skills/`. They provide step-by-step workflows that teach the AI agent how to accomplish specific tasks using the MCP tools.

### 10.1 Web Target Configuration Skill

**Path:** `config/skills/saw-web-target-configuration/SKILL.md`
**Length:** 413 lines
**Install:** Hard-link to `~/.cursor/skills/saw-web-target-configuration/SKILL.md`

**Frontmatter:**
```yaml
name: saw-web-target-configuration
description: Configure Snyk API&Web web application targets with authentication, login sequences, 2FA, and logout detection. Use when creating web app targets with form-based or sequence-based authentication.
```

**Key Sections:**

1. **Multiple Targets — Parallel Subagents:** When the user provides multiple targets, launch ALL subagents in a single message (max 10). Each subagent prompt should be short — just target details + instruction to read the skill file. Do NOT embed full skill text.

2. **Step 1: Gather Information:** Collect target URL, name (priority: user-provided > page `<title>` > FQDN), labels (user-specified only, or omit for default), credentials, 2FA requirements. Prefer login sequence (Playwright) over form login.

3. **Step 2: Login Sequence (Playwright Available):**
   - Navigate to target, find login page.
   - **Inspect form elements** using a specific JavaScript snippet that auto-detects single-page vs. multi-step login. This script identifies username field, password field, and submit button with proper CSS selectors.
   - Fill credentials and submit. For 2FA, use `probely_generate_totp` for live code, then `probely_configure_2fa_totp` for the target config.
   - Verify login success, record post-login URL.
   - **Check if login selectors exist post-login** (for logout detection accuracy).
   - **Detect extra hosts** using a multi-layered approach:
     - **Layer 1:** Network request capture (`browser_network_requests()`) at two checkpoints (before login, after login). Retry up to 3 times on failure.
     - **Layer 2:** JavaScript introspection via `browser_evaluate` to find API base URLs in `__NEXT_DATA__`, env/config globals, inline scripts, meta tags.
   - Generate sequence JSON with `[CUSTOM_USERNAME]`/`[CUSTOM_PASSWORD]` placeholders.

4. **Tool Call Order:**
   1. `probely_create_target(name, url, desc?, labels?)`
   2. `probely_configure_2fa_totp(targetId, otp_secret)` (if 2FA needed, BEFORE sequence)
   3. `probely_create_sequence(targetId, name, content, custom_field_mappings=[...])`
   4. `probely_configure_sequence_login(targetId, enabled=True)`
   5. `probely_configure_logout_detection(targetId, enabled=True, check_session_url=..., logout_detector_type=..., logout_detector_value=..., logout_condition=...)`
   6. `probely_create_extra_host(targetId, hostname, ip_address="")` (for each detected host)

5. **Logout Detection Configuration:**
   - `check_session_url`: Full absolute URL of post-login page (or different page if login selectors persist).
   - Logout detector: CSS selector from login form that only exists when logged out.
   - If selector exists on post-login page, use a more specific scoped selector (e.g., `#formlogin input[name='username']`).
   - `logout_condition`: `"any"` (default, OR) or `"all"` (AND fallback when selectors aren't unique to login page).

6. **Login Sequence JSON Format:** Array of step objects with `type`, `timestamp`, `css`, `xpath`, `value`, `frame` fields. Supported types: `goto`, `click`, `dblclick`, `fill_value`, `fill_otp`, `change`, `press_key`, `mouseover`.

7. **Step 3: Form Login (No Playwright):** Simple `probely_configure_form_login()` as fallback.

8. **Summary Table:** Always ends with a table including target ID, name, URL, login sequence status, logout detection, extra hosts, and SAW link (`https://plus.probely.app/targets/{targetId}`).

### 10.2 API Target Configuration Skill

**Path:** `config/skills/saw-api-target-configuration/SKILL.md`
**Length:** 60 lines
**Install:** Hard-link to `~/.cursor/skills/saw-api-target-configuration/SKILL.md`

**Frontmatter:**
```yaml
name: saw-api-target-configuration
description: Configure Snyk API&Web API targets from OpenAPI/Swagger schemas or Postman collections. Use when creating API targets for security scanning.
```

**Workflow:**
1. **Target name:** User-provided > schema title/collection name > domain-derived.
2. **Step 1:** Obtain API schema (OpenAPI/Swagger URL or file, Postman collection, or offer to generate from codebase).
3. **Step 2:** Create target via `probely_create_api_target_from_postman()` or `probely_create_api_target_from_openapi()`. Validate OpenAPI schemas before uploading.
4. **Step 3:** Configure API authentication if needed (API key, Bearer, OAuth, Basic Auth) via `probely_update_target_settings`.
5. **Summary table** with SAW link.

### 10.3 Snyk Code Scanning Skill (related, not part of SAW server)

**Path:** `~/.cursor/skills/snyk-rules/SKILL.md`

```yaml
name: snyk-rules
description: After making any code changes, ensure best security practices are met
```

Instructs the agent to:
- Run `snyk_code_scan` after code changes.
- Fix any issues found.
- Rescan until clean.

---

## 11. Rules

The rules file (`.mdc` format) defines behavioral constraints for AI agents using the SAW MCP server. It is hard-linked from `config/saw_rules.mdc` into each project as `.cursor/rules/saw_rules.mdc`.

**Path:** `config/saw_rules.mdc`
**Frontmatter:**
```yaml
description: Snyk API&Web (SAW) behavioral rules - safety constraints, proactive monitoring, and vulnerability handling.
alwaysApply: true
```

### Rule Categories

**1. CRITICAL: Always Use SAW MCP Server Tools**
- NEVER call the Probely API directly via HTTP.
- NEVER write scripts, use curl, or create helper files as workarounds.
- Always use `probely_*` MCP tools.
- If a tool call fails, fix parameters and retry — don't bypass.
- MCP tools handle formatting (e.g., pretty-printing login sequences).

**2. Trigger Keywords**
Use SAW tools when user mentions: "Snyk API&Web", "SAW", "Probely", "DAST", "security scan", "vulnerability scan", "web scan", "target" (security context), "findings", "vulnerabilities".

**3. Automatic Target Discovery**
On workspace load, check if it's an app/API codebase. If yes, search for existing SAW targets via `probely_list_targets`. Inform user of coverage or suggest creating a target. Skip for non-app projects (libraries, CLIs, docs).

**4. NEVER Start Scans Automatically**
Scans are intrusive. Only start when user explicitly requests. Recommend quick scan profile first.

**5. Vulnerability Remediation**
- Do NOT modify codebase directly.
- Use `probely_get_finding` for details (CVSS, endpoints, fix recommendations).
- Create a patch file or `SECURITY_FIXES.md` with fixes.
- Alert user and let them review/apply.

**6. Security Scan Recommendations**
Suggest scans when working on security-sensitive code. Use severity filters for high/critical findings.

**7. Active Scan Monitoring**
Check progress every 5 minutes. Show progress delta, ETA, new vulnerabilities, severity breakdown. On completion, offer to list findings, generate report, or analyze high-risk items.

**8. Finding Management**
Mark findings as `fixed`, `false_positive`, or `accepted_risk` using update tools.

**9. Multiple Targets: Parallel Subagents**
Launch separate `generalPurpose` subagents for each target. All Task tool calls in a single message. Keep prompts short. Subagents must NOT search the workspace (it's unrelated to target config).

**10. Reporting**
Generate reports when multiple vulnerabilities are fixed, before major releases, or for compliance documentation.

---

## 12. Scripts & Packaging

### 12.1 Development Server (`scripts/dev.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$PROJECT_DIR"
source venv/bin/activate
fastmcp dev snyk_apiweb/server.py
```

Starts FastMCP in dev mode with hot-reload for development.

### 12.2 MCP Inspector (`scripts/inspector.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$PROJECT_DIR"
source venv/bin/activate
npx @modelcontextprotocol/inspector python -m snyk_apiweb.server
```

Opens a web UI for interactive tool browsing and testing. Requires Node.js/npx.

### 12.3 Packaging (`scripts/package.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail
```

1. Creates a staging directory (`mktemp -d`) with cleanup trap.
2. Copies project via `rsync`, excluding `venv`, `dist`, `node_modules`, `.git`, `__pycache__`, `distribution`.
3. **Redacts the API key** in the staged `config/config.yaml` using `sed` (replaces any `api_key` value with `"CHANGEME"`).
4. Creates `dist/SnykAPIWeb-<version>.tgz` from staging (version from `__init__.py`).

---

## 13. IDE Integration

### Cursor MCP Configuration (`mcp.json`)

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
}
```

### Installing Skills (hard links, not copies)

```bash
mkdir -p ~/.cursor/skills/saw-web-target-configuration
mkdir -p ~/.cursor/skills/saw-api-target-configuration
ln /<basedir>/saw-mcpserver/config/skills/saw-web-target-configuration/SKILL.md ~/.cursor/skills/saw-web-target-configuration/SKILL.md
ln /<basedir>/saw-mcpserver/config/skills/saw-api-target-configuration/SKILL.md ~/.cursor/skills/saw-api-target-configuration/SKILL.md
```

### Installing Rules (hard links, per project)

```bash
mkdir -p .cursor/rules
ln /<basedir>/saw-mcpserver/config/saw_rules.mdc .cursor/rules/saw_rules.mdc
```

Hard links ensure a single source of truth. Updates via `git pull` propagate automatically.

---

## 14. Security Practices

1. **API key storage:** Only in `config/config.yaml` (never in IDE-global config, never hardcoded).
2. **Config file:** Gitignored (`config/config.yaml`). Only the template (`config.yaml.dist`) is committed.
3. **File permissions:** Recommend `chmod 600 config/config.yaml`.
4. **Packaging:** The `package.sh` script redacts the API key before creating the tarball.
5. **Auth header:** `Authorization: JWT {api_key}` — no Bearer prefix, uses JWT format.
6. **HTTPS:** All API calls use HTTPS via the Probely base URL.

---

## 15. Gitignore

```
node_modules/
dist/
*.log
.env
venv
config/config.yaml
.DS_Store
*.tgz
__pycache__

# Snyk Security Extension - AI Rules (auto-generated)
.cursor/rules/snyk_rules.mdc
```

Note: `config/config.yaml` (runtime, with real API key) is gitignored. `config/config.yaml.dist` (template) is committed.

---

## Appendix A: Form Element Inspection Script

This JavaScript snippet (used in the web target configuration skill) is run via Playwright's `browser_evaluate` to auto-detect login form elements. It handles both single-page and multi-step login flows:

```javascript
() => {
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
    d.selector = el.name
      ? `${el.tagName.toLowerCase()}[type="${el.type || 'submit'}"][name="${el.name}"]`
      : d.selector;
    return d;
  };

  const passwordField = document.querySelector('input[type="password"]');

  if (passwordField) {
    // Single-page login
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
    return { step: 'single_page', username: describe(usernameField), password: describe(passwordField), submit: describeSubmit(submitEl) };
  }

  // Multi-step login
  const candidates = Array.from(document.querySelectorAll(
    'input[type="text"], input[type="email"], input[name*="user"], input[name*="email"], input[name*="login"]'
  )).filter(el => el.offsetParent !== null);
  let primaryInput = null;
  for (const el of candidates) {
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

## Appendix B: Extra Host Detection Script

JavaScript snippet for detecting API hosts in the post-login page context:

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

  if (window.__NEXT_DATA__) extractHosts(JSON.stringify(window.__NEXT_DATA__));

  for (const key of Object.keys(window)) {
    if (/env|config|settings|api/i.test(key)) {
      try { extractHosts(JSON.stringify(window[key])); } catch {}
    }
  }

  document.querySelectorAll('script:not([src])').forEach(s => extractHosts(s.textContent));
  document.querySelectorAll('meta[content*="http"]').forEach(m => extractHosts(m.content));

  return { apiHosts: [...found], targetHost };
}
```

---

*End of AppBuilder specification. This document contains everything needed to rebuild the SAW MCP Server from scratch.*
