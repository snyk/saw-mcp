# Installing Snyk API & Web MCP in Windsurf

Windsurf natively integrates with the Model Context Protocol (MCP), allowing you to bring custom tools like this one into your Cascade coding assistant.

There are two ways to add the Snyk API & Web MCP server to Windsurf.

## Option 1: Using the UI (Recommended)

1. Open Windsurf.
2. Click on the **MCPs icon** (the plug/connection icon) in the top right menu of the **Cascade panel**, or go to **Windsurf Settings > Cascade > MCP Servers**.
3. At the bottom or top of the MCP list, you can click on **"Add MCP"** or find the option to edit the raw `mcp_config.json`.
4. If you have the option to configure it visually, set the following:
   * **Name**: `SAW`
   * **Command**: `uvx`
   * **Arguments**: `--from`, `git+https://github.com/snyk/saw-mcp.git`, `saw-mcp`
   * **Environment Variables**: Add `MCP_SAW_API_KEY` and set it to your API key.

## Option 2: Editing `mcp_config.json` manually

Windsurf stores your custom MCP server configurations in `~/.codeium/windsurf/mcp_config.json`.

1. Open your terminal and open the config file in your editor:
   ```bash
   code ~/.codeium/windsurf/mcp_config.json
   # or
   nano ~/.codeium/windsurf/mcp_config.json
   ```

2. Add the `SAW` entry under the `mcpServers` object:
   ```json
   {
     "mcpServers": {
       "SAW": {
         "command": "uvx",
         "args": [
           "--from",
           "git+https://github.com/snyk/saw-mcp.git",
           "saw-mcp"
         ],
         "env": {
           "MCP_SAW_API_KEY": "your-api-key-here"
         }
       }
     }
   }
   ```
   *(If you already have other servers like "github" or "memory" in this file, just add "SAW" alongside them).*

3. Save the file.
4. Restart Windsurf or refresh the Cascade panel.
5. Open the **MCPs icon** in Cascade and make sure the `SAW` tools are toggled **ON**.

## Verifying the Installation

Open the Cascade chat panel and type:
> "What Snyk API & Web (Probely) tools do you have access to?"

Cascade should list the available tools (like creating targets, starting scans, etc.), confirming that the integration is working!
