#!/usr/bin/env bash
# Store API key (and optional base URL) in .env for persistent use across
# terminal sessions and Cursor.  .env is gitignored and loaded automatically
# at server startup.
#
# Updates MCP_SAW_API_KEY in place when .env already exists, preserves
# unrelated entries and comments, and only touches MCP_SAW_BASE_URL when
# --base-url is supplied.
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
ENV_FILE=".env"
BASE_URL=""
API_KEY=""
CREATED=0

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

# Upsert KEY=VALUE in ENV_FILE. Replaces the first matching assignment,
# drops later duplicates of the same key, appends when missing. Other lines
# (including comments and blank lines) are left unchanged.
upsert_env_var() {
  local key="$1"
  local value="$2"
  local tmp
  local found=0
  local line
  local prefix

  tmp="$(mktemp "${TMPDIR:-/tmp}/saw-env.XXXXXX")"

  if [ -f "$ENV_FILE" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
      prefix="${line%%=*}"
      if [ "$prefix" = "$key" ]; then
        if [ "$found" -eq 0 ]; then
          printf '%s=%s\n' "$key" "$value"
          found=1
        fi
      else
        printf '%s\n' "$line"
      fi
    done < "$ENV_FILE" > "$tmp"
  fi

  if [ "$found" -eq 0 ]; then
    printf '%s=%s\n' "$key" "$value" >> "$tmp"
  fi

  if ! mv "$tmp" "$ENV_FILE"; then
    rm -f "$tmp"
    return 1
  fi
}

# ── Write .env ───────────────────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  CREATED=1
  : > "$ENV_FILE"
fi

upsert_env_var "MCP_SAW_API_KEY" "$API_KEY"
if [ -n "$BASE_URL" ]; then
  upsert_env_var "MCP_SAW_BASE_URL" "$BASE_URL"
fi
chmod 600 "$ENV_FILE"

if [ "$CREATED" -eq 1 ]; then
  if [ -z "$BASE_URL" ]; then
    echo "Created .env with your API key (permissions: owner-only)."
  else
    echo "Created .env for $BASE_URL (permissions: owner-only)."
  fi
else
  if [ -z "$BASE_URL" ]; then
    echo "Updated .env with your API key (permissions: owner-only)."
  else
    echo "Updated .env for $BASE_URL (permissions: owner-only)."
  fi
fi
