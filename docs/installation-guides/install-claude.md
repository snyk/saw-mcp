# Claude Desktop

Add the following to your Claude Desktop MCP configuration file.

Replace `/<basedir>/saw-mcp` with the absolute path to this repo.

## Prerequisites

### Browser Automation (playwright-cli)

Web target configuration records login sequences using a real browser via `playwright-cli`. Run once after cloning:

```bash
./scripts/setup-playwright.sh
```

Requires Node.js 18+. This installs `@playwright/cli` globally and downloads the Chromium binary.

## Configuration

Run `./scripts/setup-env.sh` once to store your API key, then add:

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

The server picks up your API key from `.env` automatically. No key in the config block needed.

### Alternatives

- **Pass the key directly:** add `"MCP_SAW_API_KEY": "your-api-key"` to the `env` block.
- **Override the base URL** (e.g. staging): add `"MCP_SAW_BASE_URL": "https://api.staging.probely.dev"`.
- **Use a config file:** set `"MCP_SAW_CONFIG_PATH": "/<basedir>/saw-mcp/config/config.yaml"` instead.
- **Set log level:** add `"MCP_SAW_LOG_LEVEL": "DEBUG"` (options: DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO).
