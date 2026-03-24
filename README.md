![SAW MCP Banner](./assets/Snyk_API_and_Web_Banner.webp)

# Snyk API & Web MCP Server

Connect your AI coding assistant to Snyk API & Web so it can onboard scan targets, configure authentication, run DAST scans, and triage findings — all through natural language.

Built on FastMCP 2.0, works with Cursor, Claude Code, Devin, Windsurf, and any MCP-compatible client.

> **Naming note:** Snyk API & Web was formerly known as Probely. The API endpoints (`api.probely.com`), web console (`plus.probely.app`), and MCP tool names (`probely_*`) still use the legacy domain and prefix. Environment variables and config sections use the new `SAW` / `saw` naming.

See **[USER_GUIDE.md](USER_GUIDE.md)** for usage, examples, and tool reference.

> **This repository is closed to public contributions.** We appreciate community interest, but we do not accept pull requests, issues, or other contributions from external contributors at this time. If you have found a security issue, please see [SECURITY.md](SECURITY.md).

## Requirements

- Python 3.10+
- Snyk API & Web API key

## Quick Start

### 1. Get Your API Key

Go to [https://plus.probely.app/api-keys](https://plus.probely.app/api-keys) and create an API key.

> **Important**
>
> Use a **custom role, limited-scope API key** for the Snyk API & Web MCP Server.
> Create the key only with the permissions required for the intended actions.
> Do not use a highly privileged or global API key, as this can affect your entire account and its resources.

### 2. Install

#### Cursor Marketplace (recommended)

Install directly from the [Cursor Marketplace](https://cursor.com/marketplace):

1. Open Cursor and go to **Settings → Plugins**
2. Search for **Snyk API & Web**
3. Click **Install**
4. Set your API key as an environment variable:
   ```bash
   export MCP_SAW_API_KEY="your-api-key"
   ```

The plugin installs the MCP server, rules, and skills automatically.

#### One-command install (any MCP client)

```bash
uvx --from git+https://github.com/snyk/saw-mcp.git saw-mcp
```

Or add to your MCP client configuration:

```json
{
  "mcpServers": {
    "SAW": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/snyk/saw-mcp.git", "saw-mcp"],
      "env": {
        "MCP_SAW_API_KEY": "your-api-key"
      }
    }
  }
}
```

<details>
<summary>Alternative installation methods</summary>

**Install from release tarball**

```bash
tar -xzvf SnykAPIWeb-<version>.tgz
cd SnykAPIWeb
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Download from [Releases](https://github.com/snyk/saw-mcp/releases) and replace `<version>` with the actual version number (e.g., `1.0.0`).

**Clone from source**

```bash
git clone https://github.com/snyk/saw-mcp.git
cd saw-mcp
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

</details>

### 3. Store Your API Key

The server reads your API key from (in order of precedence): environment variable `MCP_SAW_API_KEY` → `.env` file → `config/config.yaml`.

**Option A: Environment variable** (recommended for Marketplace / `uvx` installs)

```bash
export MCP_SAW_API_KEY="your-api-key"
```

**Option B: `.env` file** (recommended for source installs)

Run the setup script (prompts securely, no key in shell history):

```bash
./scripts/setup-env.sh
```

Or pipe from a secret manager: `op read 'op://vault/item/key' | ./scripts/setup-env.sh`

This writes a `.env` file in the project root (gitignored). The server loads it automatically at startup.

### 4. Configure Your IDE

If you installed from the Cursor Marketplace, configuration is automatic. For other clients, add to your MCP client configuration:

```json
{
  "mcpServers": {
    "SAW": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/snyk/saw-mcp.git", "saw-mcp"],
      "env": {
        "MCP_SAW_API_KEY": "your-api-key"
      }
    }
  }
}
```

For host-specific setup see the [Installation Guides](docs/installation-guides/).

<details>
<summary>Additional configuration options</summary>

- **Override the base URL:** add `"MCP_SAW_BASE_URL": "https://your-instance-url"` to the `env` block.
- **Use a config file:** set `"MCP_SAW_CONFIG_PATH": "/path/to/config.yaml"` instead.
- **Set log level:** add `"MCP_SAW_LOG_LEVEL": "DEBUG"` (options: DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO).

</details>

### 5. Start Using

Ask your AI assistant to:

- "Configure a Snyk API & Web API target from this OpenAPI schema / Swagger document / Postman collection."
- "Configure a Snyk API & Web web target for this authenticated application."

See **[prompts.md](prompts.md)** for a full catalog of example prompts — from simple one-liners to complex multi-target workflows.

## IDE Integration

Detailed per-host guides live in [`docs/installation-guides/`](docs/installation-guides/):

| Host | Guide |
|------|-------|
| **Cursor** | [install-cursor.md](docs/installation-guides/install-cursor.md) |
| **Claude Desktop** | [install-claude.md](docs/installation-guides/install-claude.md) |
| **Devin / Other IDEs** | [install-devin.md](docs/installation-guides/install-devin.md) |

## Packaging

```bash
bash scripts/package.sh
```

Creates `dist/SnykAPIWeb-<version>.tgz` (version from `snyk_apiweb/__init__.py`).

## Development & Testing

### Run the Server (standalone)

Running the server directly starts it and waits for an MCP client connection. This is mainly useful for **development and debugging**:

```bash
./venv/bin/python -m snyk_apiweb.server
```

### Development Mode (hot reload)

For active development with automatic reload on file changes:

```bash
./scripts/dev.sh
```

## License

This project is licensed under the [Apache License 2.0](LICENSE).
