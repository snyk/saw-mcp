#!/usr/bin/env bash
# Store API key in .env for persistent use across terminal sessions and Cursor.
# .env is gitignored and loaded automatically at server startup.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ "$#" -eq 1 ]; then
  echo "MCP_SAW_API_KEY=$1" > .env
  echo "Created .env with your API key."
else
  if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || echo "MCP_SAW_API_KEY=" > .env
    echo "Created .env. Edit it and add your API key from https://plus.probely.app/api-keys"
  else
    echo ".env exists. Add MCP_SAW_API_KEY=your-key if not already set."
  fi
fi
