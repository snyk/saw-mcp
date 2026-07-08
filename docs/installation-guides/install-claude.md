# Claude Desktop

Add one of the following to your Claude Desktop MCP configuration file.

## Option A: `uvx` (recommended)

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

## Browser Automation for Web Targets

Web targets with login sequences require browser automation. SAW MCP does not include a browser.

**Preferred (coding agents with Shell):**

```bash
npm install -g @playwright/cli@latest
playwright-cli install-browser chromium
```

**Fallback (MCP-only clients such as Claude Desktop):** add [Playwright MCP](https://playwright.dev/docs/getting-started-mcp):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    }
  }
}
```

Without either, the AI falls back to form login for simple login pages only.

## Option B: Local clone

Replace `/<basedir>/saw-mcp` with the absolute path to this repo. Run `./scripts/setup-env.sh` once to store your API key, then add:

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

### Additional options

- **Pass the key directly:** add `"MCP_SAW_API_KEY": "your-api-key"` to the `env` block.
- **Override the base URL:** add `"MCP_SAW_BASE_URL": "https://your-instance-url"`.
- **Use a config file:** set `"MCP_SAW_CONFIG_PATH": "/<basedir>/saw-mcp/config/config.yaml"` instead.
- **Set log level:** add `"MCP_SAW_LOG_LEVEL": "DEBUG"` (options: DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO).
