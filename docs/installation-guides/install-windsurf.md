# Windsurf

Windsurf integrates with the Model Context Protocol (MCP), allowing you to bring the Snyk API & Web MCP server into Cascade.

## Windsurf Marketplace (recommended)

The Snyk API & Web MCP Server is listed on the [Windsurf Marketplace](https://windsurf.com/marketplace).

1. Open Windsurf.
2. Click the **MCPs icon** in the top-right of the **Cascade panel**, or go to **Windsurf Settings → Cascade → MCP Servers**.
3. Search for **Snyk API & Web** and click **Install**.
4. When prompted, enter your API key (create one at [plus.probely.app/api-keys](https://plus.probely.app/api-keys)).

Windsurf handles the `mcp_config.json` entry automatically.

## Manual configuration

Windsurf stores MCP server configurations in `~/.codeium/windsurf/mcp_config.json`.

### Option A: `uvx` (recommended)

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

### Option B: Local clone

Replace `/<basedir>/saw-mcp` with the absolute path to this repo. Run `./scripts/setup-env.sh` once, then add:

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

### Additional options

- **Pass the key directly:** add `"MCP_SAW_API_KEY": "your-api-key"` to the `env` block.
- **Override the base URL:** add `"MCP_SAW_BASE_URL": "https://your-instance-url"`.
- **Use a config file:** set `"MCP_SAW_CONFIG_PATH": "/<basedir>/saw-mcp/config/config.yaml"` instead.
- **Set log level:** add `"MCP_SAW_LOG_LEVEL": "DEBUG"` (options: DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO).

Save the file, then restart Windsurf or refresh the Cascade panel. Open the **MCPs icon** in Cascade and ensure the `SAW` tools are toggled **ON**.

## Verifying the connection

Open Cascade and ask:

> What Snyk API & Web tools do you have access to?

Cascade should list the available tools, confirming the integration is working.
