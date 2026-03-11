#!/usr/bin/env bash
# Store API key in .env for persistent use across terminal sessions and Cursor.
# .env is gitignored and loaded automatically at server startup.
#
# Usage:
#   ./scripts/setup-env.sh              # interactive prompt (recommended)
#   op read ... | ./scripts/setup-env.sh  # pipe from 1Password / secret manager
#   ./scripts/setup-env.sh YOUR_KEY     # argument (exposes key in shell history)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ "$#" -eq 1 ]; then
  API_KEY="$1"
  echo "Warning: passing keys as arguments exposes them in shell history."
  echo "Prefer: ./scripts/setup-env.sh  (interactive prompt)"
elif [ -t 0 ] && [ "$#" -eq 0 ]; then
  printf "Paste your API key (from https://plus.probely.app/api-keys — Snyk API&Web console): "
  read -rs API_KEY
  echo
else
  read -r API_KEY
fi

if [ -z "${API_KEY:-}" ]; then
  echo "Error: empty API key." >&2
  exit 1
fi

echo "MCP_SAW_API_KEY=$API_KEY" > .env
chmod 600 .env
echo "Created .env with your API key (permissions: owner-only)."
