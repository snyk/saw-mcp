# Devin and Other IDEs

Use the same command and args as the other installation guides. Set the appropriate environment variables for your IDE.

Replace `/<basedir>/saw-mcp` with the absolute path to this repo.

## Prerequisites

### Browser Automation (playwright-cli)

Web target configuration records login sequences using a real browser via `playwright-cli`. Run once after cloning:

```bash
./scripts/setup-playwright.sh
```

Requires Node.js 18+. This installs `@playwright/cli` globally and downloads the Chromium binary.

## Configuration

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
