#!/usr/bin/env bash
# Store API key (and optional base URL) in .env for persistent use across
# terminal sessions and Cursor.  .env is gitignored and loaded automatically
# at server startup.
#
# Usage:
#   ./scripts/setup-env.sh                              # production (default)
#   ./scripts/setup-env.sh --base-url https://api.x.y   # custom API endpoint
#   op read ... | ./scripts/setup-env.sh                 # pipe from secret manager
#   ./scripts/setup-env.sh YOUR_KEY                      # argument (exposes key in history)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

PROD_CONSOLE="https://plus.probely.app/api-keys"
BASE_URL=""
API_KEY=""

# ── Parse arguments ──────────────────────────────────────────────────────────
while [ "$#" -gt 0 ]; do
  case "$1" in
    --base-url|-u)
      shift
      BASE_URL="${1:-}"
      if [ -z "$BASE_URL" ]; then
        echo "Error: --base-url requires a URL argument." >&2
        exit 1
      fi
      shift
      ;;
    -*)
      echo "Error: unknown option '$1'" >&2
      exit 1
      ;;
    *)
      API_KEY="$1"
      echo "Warning: passing keys as arguments exposes them in shell history."
      echo "Prefer: ./scripts/setup-env.sh  (interactive prompt)"
      shift
      ;;
  esac
done

# ── Read API key (interactive or piped) ──────────────────────────────────────
if [ -z "$API_KEY" ]; then
  if [ -t 0 ]; then
    if [ -z "$BASE_URL" ]; then
      printf "Paste your API key (from %s): " "$PROD_CONSOLE"
    else
      printf "Paste your API key for %s: " "$BASE_URL"
    fi
    read -rs API_KEY
    echo
  else
    read -r API_KEY
  fi
fi

if [ -z "${API_KEY:-}" ]; then
  echo "Error: empty API key." >&2
  exit 1
fi

# ── Write .env ───────────────────────────────────────────────────────────────
{
  echo "MCP_SAW_API_KEY=$API_KEY"
  if [ -n "$BASE_URL" ]; then
    echo "MCP_SAW_BASE_URL=$BASE_URL"
  fi
} > .env
chmod 600 .env

if [ -z "$BASE_URL" ]; then
  echo "Created .env with your API key (permissions: owner-only)."
else
  echo "Created .env for $BASE_URL (permissions: owner-only)."
fi
