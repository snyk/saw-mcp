# Devin and Other IDEs

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

## Option B: Local clone

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
