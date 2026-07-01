# Installing Snyk API & Web MCP in Devin

## Option 1: Devin MCP Marketplace (Recommended)

The Snyk API & Web MCP Server is available from Devin's MCP Marketplace and can be installed without editing MCP configuration files manually.

1. Open Devin and go to **Settings → Configuration**.
2. Under **MCP servers**, click **Open MCP Marketplace**.
3. Search for **Snyk API & Web** and click **Install**.
4. When prompted, enter your API key (create one at [plus.probely.app/api-keys](https://plus.probely.app/api-keys)).

Devin handles the MCP server setup automatically — no manual configuration needed.

## Option 2: `uvx`

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) installed. No local clone needed.

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

## Option 3: Local clone

Replace `/<basedir>/saw-mcp` with the absolute path to this repo.

## Prerequisites

### Browser Automation (playwright-cli)

Web target configuration records login sequences using a real browser via `playwright-cli`. Run once after cloning:

```bash
./scripts/setup-playwright.sh
```

Requires Node.js 18+. This installs `@playwright/cli` globally and downloads the Chromium binary.
```json
{
  "mcpServers": {
    "SAW": {
      "command": "/<basedir>/saw-mcp/venv/bin/python",
      "args": ["-m", "snyk_apiweb.server"],
      "env": {
        "PYTHONPATH": "/<basedir>/saw-mcp"
      }
    }
  }
}
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MCP_SAW_API_KEY` | Snyk API & Web API key | Yes (or use `.env` file) |
| `MCP_SAW_BASE_URL` | Override the API endpoint (e.g. staging) | No |
| `MCP_SAW_CONFIG_PATH` | Path to a `config.yaml` file | No |
| `MCP_SAW_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO) | No |

> **Config precedence:** environment variable → `.env` file → `config/config.yaml`

Always use absolute paths.
