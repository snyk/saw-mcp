# Cursor

1. Open **Settings → Tools & MCP → New MCP Server**
2. Paste one of the configuration blocks below (use absolute paths)
3. Save and restart Cursor

Replace `/<basedir>/saw-mcp-server` with the absolute path to this repo.

## Option A: `.env` file (recommended)

Run `./scripts/setup-env.sh` once, then use this config — no key in the JSON:

```json
{
  "mcpServers": {
    "SAW": {
      "command": "/<basedir>/saw-mcp-server/venv/bin/python",
      "args": ["-m", "snyk_apiweb.server"],
      "env": {
        "PYTHONPATH": "/<basedir>/saw-mcp-server"
      }
    }
  }
}
```

## Option B: Env var in config

```json
{
  "mcpServers": {
    "SAW": {
      "command": "/<basedir>/saw-mcp-server/venv/bin/python",
      "args": ["-m", "snyk_apiweb.server"],
      "env": {
        "PYTHONPATH": "/<basedir>/saw-mcp-server",
        "MCP_SAW_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Option C: Config file

```json
{
  "mcpServers": {
    "SAW": {
      "command": "/<basedir>/saw-mcp-server/venv/bin/python",
      "args": ["-m", "snyk_apiweb.server"],
      "env": {
        "PYTHONPATH": "/<basedir>/saw-mcp-server",
        "MCP_SAW_CONFIG_PATH": "/<basedir>/saw-mcp-server/config/config.yaml"
      }
    }
  }
}
```

## Skills and Rules

The server ships with **project rules** and **agent skills** that teach the AI how to use the tools. Link them so Cursor can find them:

```bash
# Project rules (per project)
mkdir -p .cursor/rules
ln /<basedir>/saw-mcp-server/config/saw_rules.mdc .cursor/rules/saw_rules.mdc

# Agent skills (global)
mkdir -p ~/.cursor/skills/saw-web-target-configuration ~/.cursor/skills/saw-api-target-configuration
ln /<basedir>/saw-mcp-server/config/skills/saw-web-target-configuration/SKILL.md ~/.cursor/skills/saw-web-target-configuration/SKILL.md
ln /<basedir>/saw-mcp-server/config/skills/saw-api-target-configuration/SKILL.md ~/.cursor/skills/saw-api-target-configuration/SKILL.md
```
