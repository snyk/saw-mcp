#!/usr/bin/env bash
# Install playwright-cli and download the Chromium browser binary.
# Required for the SAW web target configuration skill (login sequence recording).
#
# Usage:
#   ./scripts/setup-playwright.sh

set -euo pipefail

# ── Check Node.js / npm ───────────────────────────────────────────────────────
if ! command -v npm &>/dev/null; then
  echo "Error: npm not found. Install Node.js 18+ from https://nodejs.org and re-run." >&2
  exit 1
fi

NODE_MAJOR=$(node -e "process.stdout.write(process.versions.node.split('.')[0])" 2>/dev/null || echo "0")
if [ "$NODE_MAJOR" -lt 18 ]; then
  echo "Error: Node.js 18+ is required (found $(node --version 2>/dev/null || echo 'unknown'))." >&2
  exit 1
fi

# ── Install @playwright/cli ───────────────────────────────────────────────────
echo "Installing @playwright/cli globally..."
npm install -g @playwright/cli

# ── Verify binary is available ────────────────────────────────────────────────
if ! command -v playwright-cli &>/dev/null; then
  echo "Error: playwright-cli binary not found after install." >&2
  echo "Make sure npm global bin is on your PATH: $(npm bin -g)" >&2
  exit 1
fi

echo "playwright-cli $(playwright-cli --version 2>/dev/null || echo '(installed)') is available."

# ── Download Chromium browser binary ─────────────────────────────────────────
echo "Downloading Chromium browser binary..."
playwright-cli install chromium

echo ""
echo "Setup complete. playwright-cli is ready for browser automation."
