#!/usr/bin/env bash
# Start the MCP server in FastMCP dev mode
# Provides hot-reload and debugging features

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
source venv/bin/activate

echo "Starting Snyk API & Web MCP Server in dev mode..."
echo ""

fastmcp dev snyk_apiweb/server.py
