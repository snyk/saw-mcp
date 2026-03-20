from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

# Load .env from project root so MCP_SAW_API_KEY persists across sessions
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_project_root, ".env"), override=False)

logger = logging.getLogger(__name__)

# Support both new and legacy environment variable names
CONFIG_PATH_ENV = "MCP_SAW_CONFIG_PATH"
CONFIG_PATH_ENV_LEGACY = "MCP_PROBELY_CONFIG_PATH"
API_KEY_ENV = "MCP_SAW_API_KEY"
BASE_URL_ENV = "MCP_SAW_BASE_URL"
DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml"
)

# Allowed base directories for config paths (prevents path traversal)
_ALLOWED_CONFIG_BASES = (
    os.path.realpath(os.path.dirname(DEFAULT_CONFIG_PATH)),
    os.path.realpath(os.getcwd()),
    os.path.realpath(tempfile.gettempdir()),
)


def _resolve_and_validate_config_path(cfg_path: str) -> str:
    """Resolve path to absolute and ensure it's within allowed directories."""
    resolved = os.path.realpath(os.path.abspath(cfg_path))
    for base in _ALLOWED_CONFIG_BASES:
        if resolved == base or resolved.startswith(base + os.sep):
            return resolved
    raise ValueError(
        f"Config path {cfg_path!r} resolves outside allowed directories. "
        "Use a path under the project config dir or current working directory."
    )


def load_config(path: str | None = None) -> Dict[str, Any]:
    """Load configuration from YAML file.

    When MCP_SAW_API_KEY is set, the config file is optional. If absent,
    returns an empty dict (env-only mode). If present, loads it for
    target_defaults, tool_filter, etc.
    """
    cfg_path = (
        path
        or os.environ.get(CONFIG_PATH_ENV)
        or os.environ.get(CONFIG_PATH_ENV_LEGACY)
        or DEFAULT_CONFIG_PATH
    )
    # Env-only mode: MCP_SAW_API_KEY set and config file absent → no config needed
    if os.environ.get(API_KEY_ENV):
        if not os.path.isfile(cfg_path):
            logger.info(
                "Using %s from environment (no config file)", API_KEY_ENV
            )
            return {}
        validated_path = _resolve_and_validate_config_path(cfg_path)
        logger.info("Loading config from %s", validated_path)
        with open(validated_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    # No env key: require config file
    validated_path = _resolve_and_validate_config_path(cfg_path)
    if not os.path.isfile(validated_path):
        raise FileNotFoundError(
            f"Config file not found: {validated_path}. "
            f"Set {API_KEY_ENV} or create a config file."
        )
    logger.info("Loading config from %s", validated_path)
    with open(validated_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def get_probely_base_url(cfg: Dict[str, Any]) -> str:
    """Get the Snyk API & Web base URL from env or config.

    Precedence: MCP_SAW_BASE_URL env var → saw.base_url → probely.base_url → default.
    Supports both 'saw' (new) and 'probely' (legacy) config sections.
    """
    env_url = os.environ.get(BASE_URL_ENV, "").strip()
    if env_url:
        return env_url

    saw_cfg = cfg.get("saw", {})
    probely_cfg = cfg.get("probely", {})

    base_url = saw_cfg.get("base_url") or probely_cfg.get(
        "base_url", "https://api.probely.com"
    )
    return base_url


def get_probely_api_key(cfg: Dict[str, Any]) -> str:
    """Get the Snyk API & Web API key from env or config.

    Precedence: MCP_SAW_API_KEY env var → saw.api_key → probely.api_key.
    Supports both 'saw' (new) and 'probely' (legacy) config sections.
    """
    key = (os.environ.get(API_KEY_ENV) or "").strip()
    if not key:
        saw_cfg = cfg.get("saw", {})
        probely_cfg = cfg.get("probely", {})
        key = (
            saw_cfg.get("api_key") or probely_cfg.get("api_key") or ""
        ).strip()
    if not key or key in (
        "REPLACE_WITH_YOUR_SAW_API_KEY",
        "REPLACE_WITH_YOUR_PROBELY_API_KEY",
        "CHANGEME",
    ):
        raise RuntimeError(
            f"Snyk API & Web API key not set. Set {API_KEY_ENV} or update "
            "config/config.yaml 'saw.api_key' / 'probely.api_key'."
        )
    if len(key) < 20:
        logger.warning(
            "API key looks unusually short (%d chars). "
            "Make sure you copied the full key, not the key ID.",
            len(key),
        )
    return key


def get_target_defaults(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Get default settings auto-applied to new targets.

    Returns a dict that may contain:
    - default_label: a ``{"name": "..."}`` dict ready for the Probely target
      API, or ``None`` if not configured.  The API resolves labels by name
      (reuses existing, creates missing) so no ID or lookup is needed.
    - name_prefix: a string prepended to every target name (e.g. ``"Agentic - "``),
      or ``""`` if not configured.
    """
    td = cfg.get("target_defaults") or {}

    default_label = None
    label_name = td.get("label") or ""
    if label_name:
        default_label = {"name": label_name}

    return {
        "default_label": default_label,
        "name_prefix": td.get("name_prefix") or "",
    }


def get_tool_filter(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Get tool filtering configuration.

    Returns a dict with:
    - enabled_tools: list of tool names to enable (whitelist), or None for all
    - disabled_tools: list of tool names to disable (blacklist), or empty list

    If enabled_tools is set, only those tools are available.
    If disabled_tools is set, all tools except those are available.
    If both are set, enabled_tools takes precedence.
    """
    tools_cfg = cfg.get("tools") or {}
    return {
        "enabled_tools": tools_cfg.get("enabled"),  # None means all enabled
        "disabled_tools": tools_cfg.get("disabled")
        or [],  # Empty means none disabled
    }


def is_tool_enabled(tool_name: str, tool_filter: Dict[str, Any]) -> bool:
    """Check if a tool should be enabled based on the filter configuration."""
    enabled_tools = tool_filter.get("enabled_tools")
    disabled_tools = tool_filter.get("disabled_tools", [])

    # If whitelist is defined, only those tools are enabled
    if enabled_tools is not None:
        return tool_name in enabled_tools

    # Otherwise, check blacklist
    return tool_name not in disabled_tools
