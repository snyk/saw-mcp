#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$PROJECT_DIR/dist"

rm -f "$DIST_DIR/SnykAPIWeb.tgz"
mkdir -p "$DIST_DIR"

# Build into a staging dir to allow redaction of secrets (e.g., API key)
TARBALL_PATH="$DIST_DIR/SnykAPIWeb.tgz"
STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGE_DIR"' EXIT

# Copy project to staging, excluding build-time artifacts
rsync -a \
  --exclude 'venv' \
  --exclude 'dist' \
  --exclude 'node_modules' \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude 'distribution' \
  "$PROJECT_DIR/" "$STAGE_DIR/SnykAPIWeb/"

# Redact API key in config/config.yaml inside the staging copy
CONFIG_FILE="$STAGE_DIR/SnykAPIWeb/config/config.yaml"
if [ -f "$CONFIG_FILE" ]; then
  # Replace any api_key value with CHANGEME while preserving indentation
  LC_ALL=C sed -i '' -E 's/^([[:space:]]*api_key:[[:space:]]*).*/\1"CHANGEME"/' "$CONFIG_FILE"
fi

# Create tarball from staging directory
( cd "$STAGE_DIR" && tar -czvf "$TARBALL_PATH" SnykAPIWeb )
echo "Created $TARBALL_PATH"
