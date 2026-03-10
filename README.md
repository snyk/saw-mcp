![SAW MCP Banner](./assets/saw-mcp-banner.webp)

# Snyk API&Web (SAW) MCP Server

An MCP server (FastMCP 2.0) that exposes the Snyk API&Web API as MCP tools. AI assistants (Cursor, Devin, Windsurf, Claude Code, etc.) can create and configure scan targets, run scans, and manage findings through natural language.

**Main goal:** Agentic target onboarding — create targets and automatically configure authentication (login sequences, 2FA), logout detection, and extra hosts.

See **[USER_GUIDE.md](USER_GUIDE.md)** for usage, examples, and tool reference.

## Requirements

- Python 3.10+
- Snyk API&Web API key

## Quick start

### 1. Get Your API Token

Go to [https://plus.probely.app/api-keys](https://plus.probely.app/api-keys) and create an API key with **global (account) scope** and **admin** role.

### 2. Store Your API Key

Store the API key in a `.env` file in the project root (gitignored) so it persists across sessions.

Automate env setup:

```bash
./scripts/setup-env.sh YOUR_API_KEY
```

Or manually: `echo 'MCP_SAW_API_KEY=your-key' > .env`

The server loads `.env` automatically at startup, so the key is available for both terminal and IDE use.

### 3. Configure Your IDE

Add to your Claude Desktop or Cursor MCP configuration:

```json
{
  "mcpServers": {
    "SAW": {
      "command": "/<basedir>/saw-mcpserver/venv/bin/python",
      "args": ["-m", "snyk_apiweb.server"],
      "env": {
        "PYTHONPATH": "/<basedir>/saw-mcpserver"
      }
    }
  }
}
```

Replace `/<basedir>/saw-mcpserver` with the absolute path to your `saw-mcpserver` directory. The server loads your API key from `.env` (step 2) automatically.

Optional: To pass the key via env instead, add `"MCP_SAW_API_KEY": "your-api-key"` to the `env` block.

**Config file alternative:** Use `MCP_SAW_CONFIG_PATH` instead to point to a `config.yaml` file. See [IDE integration](#ide-integration) for details.

### 4. Start Using

Ask your AI assistant to:

- "Help me configure a new API target"
- "List the most recent findings of target X"
- "Start a scan on target X"
- "Show me the findings for target Y"

## Setup (config file)

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
tar -xzvf SnykAPIWeb-*.tgz
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

**Option A: Env var (no config file)**

```json
{
  "mcpServers": {
    "SAW": {
      "command": "/<basedir>/saw-mcpserver/venv/bin/python",
      "args": ["-m", "snyk_apiweb.server"],
      "env": {
        "PYTHONPATH": "/<basedir>/saw-mcpserver",
        "MCP_SAW_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Option B: Config file**

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

Use the same command and args. Set `MCP_SAW_API_KEY` (env-only) or `MCP_SAW_CONFIG_PATH` to your `config.yaml`. Use absolute paths if your IDE does not resolve relative paths.

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

Creates `dist/SnykAPIWeb-<version>.tgz` (version from `snyk_apiweb/__init__.py`).
