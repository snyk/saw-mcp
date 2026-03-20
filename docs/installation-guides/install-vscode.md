# VS Code

VS Code supports MCP servers via the GitHub Copilot extension (requires Copilot Chat).

Replace `/<basedir>/saw-mcp` with the absolute path to this repo.

## Prerequisites

### Browser Automation (playwright-cli)

Web target configuration records login sequences using a real browser via `playwright-cli`. Run once after cloning:

```bash
./scripts/setup-playwright.sh
```

Requires Node.js 18+. This installs `@playwright/cli` globally and downloads the Chromium binary.

## Option A: Workspace config (recommended)

Create `.vscode/mcp.json` at the root of your project:

Run `./scripts/setup-env.sh` once, then use this config — no key in the JSON:

```json
{
  "servers": {
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

## Option B: User settings

Add to your VS Code `settings.json` (**Cmd/Ctrl + Shift + P → Preferences: Open User Settings (JSON)**):

```json
{
  "mcp": {
    "servers": {
      "SAW": {
        "command": "/<basedir>/saw-mcp/venv/bin/python",
        "args": ["-m", "snyk_apiweb.server"],
        "env": {
          "PYTHONPATH": "/<basedir>/saw-mcp"
        }
      }
    }
  }
}
```

## Option C: Env var in config

Pass the API key directly instead of using `.env`:

```json
{
  "servers": {
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

## Option D: Config file

```json
{
  "servers": {
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

## Verifying the connection

1. Open the Copilot Chat panel
2. Click the **Tools** icon (wrench) — the Snyk API & Web server should appear in the list
3. Ask Copilot a question that triggers one of the Snyk API & Web tools
