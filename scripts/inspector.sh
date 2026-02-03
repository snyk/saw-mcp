#!/usr/bin/env bash
# Start the MCP Inspector for interactive testing
# Opens a web UI to browse and call tools

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
source venv/bin/activate

echo "Starting MCP Inspector..."
echo "A browser window should open with the inspector UI."
echo ""

npx @modelcontextprotocol/inspector python -m snyk_apiweb.server
