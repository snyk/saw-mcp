# Cursor

## Cursor Marketplace (recommended)

1. Open Cursor and go to **Settings → Plugins**
2. Search for **Snyk API & Web**
3. Click **Install**
4. Set your API key as an environment variable before launching Cursor:
   ```bash
   export MCP_SAW_API_KEY="your-api-key"
   ```

The plugin automatically registers the MCP server, rules, and skills. No manual configuration needed.

## Manual Configuration

If you prefer manual setup, open **Settings → Tools & MCP → New MCP Server** and paste one of the blocks below.

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

### Option B: Local clone with `.env` file

Clone the repo, run `./scripts/setup-env.sh` once, then use this config. Replace `/<basedir>/saw-mcp` with the absolute path to the repo.

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

### Option C: Local clone with env var in config

```json
{
  "mcpServers": {
    "SAW": {
      "command": "/<basedir>/saw-mcp/venv/bin/python",
      "args": ["-m", "snyk_apiweb.server"],
      "env": {
        "PYTHONPATH": "/<basedir>/saw-mcp",
        "MCP_SAW_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Option D: Local clone with config file

```json
{
  "mcpServers": {
    "SAW": {
      "command": "/<basedir>/saw-mcp/venv/bin/python",
      "args": ["-m", "snyk_apiweb.server"],
      "env": {
        "PYTHONPATH": "/<basedir>/saw-mcp",
        "MCP_SAW_CONFIG_PATH": "/<basedir>/saw-mcp/config/config.yaml"
      }
    }
  }
}
```

## Optional Environment Variables

Add these to the `env` block in any of the options above:

- **`MCP_SAW_BASE_URL`**: Override API base URL (e.g. `"https://plus.probely.app/"`)
- **`MCP_SAW_LOG_LEVEL`**: Set logging level (options: DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO)

## Skills and Rules

When installed via the Cursor Marketplace, rules and skills are loaded automatically by the plugin.

For manual installs, link them so Cursor can find them:

```bash
# Project rules (per project)
mkdir -p .cursor/rules
ln /<basedir>/saw-mcp/config/saw_rules.mdc .cursor/rules/saw_rules.mdc

# Agent skills (global)
mkdir -p ~/.cursor/skills/saw-web-target-configuration ~/.cursor/skills/saw-api-target-configuration
ln /<basedir>/saw-mcp/config/skills/saw-web-target-configuration/SKILL.md ~/.cursor/skills/saw-web-target-configuration/SKILL.md
ln /<basedir>/saw-mcp/config/skills/saw-api-target-configuration/SKILL.md ~/.cursor/skills/saw-api-target-configuration/SKILL.md
```

## Troubleshooting

- **`uvx: command not found`**: Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **`python: command not found`**: Ensure Python 3.10+ is on your PATH. On macOS: `brew install python@3.12`.
- **MCP server not appearing**: Restart Cursor after saving the config. Check **Output → MCP Logs** for errors.
- **`PermissionError` on log file**: The server writes to `~/saw-mcp.log`. Ensure write access to your home directory.
