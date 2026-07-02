#!/usr/bin/env bash
# Smoke test for playwright-cli after setup-playwright.sh.
# Verifies the CLI can open a browser, capture a snapshot, and list requests.
#
# Usage:
#   ./scripts/smoke-test-playwright.sh

set -euo pipefail

SESSION="saw-smoke-$$"

cleanup() {
  playwright-cli -s="$SESSION" close 2>/dev/null || true
}
trap cleanup EXIT

if ! command -v playwright-cli &>/dev/null; then
  echo "Error: playwright-cli not found. Run ./scripts/setup-playwright.sh first." >&2
  exit 1
fi

echo "playwright-cli version: $(playwright-cli --version)"

playwright-cli -s="$SESSION" open about:blank
playwright-cli -s="$SESSION" snapshot
playwright-cli -s="$SESSION" requests

echo "playwright-cli smoke test passed"
