# Installing Snyk API & Web MCP in Devin

## Option 1: Devin MCP Marketplace (Recommended)

The Snyk API & Web MCP Server is available from Devin's MCP Marketplace and can be installed without editing MCP configuration files manually.

1. Open Devin and go to **Settings → Configuration**.
2. Under **MCP servers**, click **Open MCP Marketplace**.
3. Search for **Snyk API & Web** and click **Install**.
4. When prompted, enter your API key (create one at [plus.probely.app/api-keys](https://plus.probely.app/api-keys)).

Devin handles the MCP server setup automatically — no manual configuration needed.

## Browser Automation for Web Targets

Web targets with login sequences require browser automation. **`playwright-cli`** is preferred for Devin (Shell access):

```bash
npm install -g @playwright/cli@latest
playwright-cli install-browser chromium
```

Alternatively, install [Playwright MCP](https://playwright.dev/docs/getting-started-mcp) from Devin's MCP Marketplace.

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
| `MCP_SAW_BASE_URL` | Override the API endpoint | No |
| `MCP_SAW_CONFIG_PATH` | Path to a `config.yaml` file | No |
| `MCP_SAW_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO) | No |

> **Config precedence:** environment variable → `.env` file → `config/config.yaml`

Always use absolute paths.
