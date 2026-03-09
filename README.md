# Snyk API&Web (SAW) MCP Server

An MCP server (FastMCP 2.0) that exposes the Snyk API&Web API as MCP tools. AI assistants (Cursor, Devin, Windsurf, etc.) can create and configure scan targets, run scans, and manage findings through natural language.

**Main goal:** Agentic target onboarding — create targets and automatically configure authentication (login sequences, 2FA), logout detection, and extra hosts.

See **[USER_GUIDE.md](USER_GUIDE.md)** for usage, examples, and tool reference.

## Requirements

- Python 3.10+
- Snyk API&Web API key

## Setup

### From source

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Edit `config/config.yaml` and set your Snyk API&Web API key:
```yaml
saw:
  base_url: "https://api.probely.com"
  api_key: "YOUR_SAW_API_KEY"
```

### From tarball

```bash
tar -xzvf SnykAPIWeb.tgz
cd SnykAPIWeb
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Then edit `config/config.yaml` with your API key.

## Run the server

```bash
./venv/bin/python -m snyk_apiweb.server
```

## IDE integration

### Cursor

1. Open Settings → Tools & MCP → New MCP Server
2. Add the JSON block below (adjust paths)
3. Save and restart Cursor

```json
{
  "mcpServers": {
    "SAW": {
      "command": "/<basedir>/saw-mcpserver/venv/bin/python",
      "args": ["-m", "snyk_apiweb.server"],
      "env": {
        "PYTHONPATH": "/<basedir>/saw-mcpserver",
        "MCP_SAW_CONFIG_PATH": "/<basedir>/saw-mcpserver/config/config.yaml"
      }
    }
  }
}
```

### Devin and other IDEs

Use the same command and args. Set `MCP_SAW_CONFIG_PATH` to your `config.yaml`. Use absolute paths if your IDE does not resolve relative paths.

## Skills and Rules

The server ships with **project rules** and **agent skills** that teach the AI how to use the tools. Link them so Cursor can find them:

```bash
# Project rules (per project)
mkdir -p .cursor/rules
ln /<basedir>/saw-mcpserver/config/saw_rules.mdc .cursor/rules/saw_rules.mdc

# Agent skills (global)
mkdir -p ~/.cursor/skills/saw-web-target-configuration ~/.cursor/skills/saw-api-target-configuration
ln /<basedir>/saw-mcpserver/config/skills/saw-web-target-configuration/SKILL.md ~/.cursor/skills/saw-web-target-configuration/SKILL.md
ln /<basedir>/saw-mcpserver/config/skills/saw-api-target-configuration/SKILL.md ~/.cursor/skills/saw-api-target-configuration/SKILL.md
```

## Packaging

```bash
bash scripts/package.sh
```

Creates `dist/SnykAPIWeb.tgz`.
