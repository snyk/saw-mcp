from __future__ import annotations

import logging
import os
import shutil
import subprocess
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

# Destructive / high-impact tools that are disabled out of the box so a
# manipulated or compromised AI session cannot invoke them silently. They must
# be opted in explicitly via the ``tools.enabled`` whitelist in the config
# file. This safe default applies even in env-only mode (no config file), so it
# cannot be bypassed by simply omitting the config.
#
# - probelyrequest: raw "call any API" passthrough that bypasses every
#   per-tool validation (note: the real tool name has no underscore).
# - probely_delete_target / probely_delete_credential: irreversible deletes.
# - probely_bulk_update_findings: can mass-resolve findings as false positives.
DEFAULT_DISABLED_TOOLS = [
    "probelyrequest",
    "probely_delete_target",
    "probely_delete_credential",
    "probely_bulk_update_findings",
]

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


_API_KEY_PLACEHOLDERS = ("CHANGEME",)


def _is_secret_reference(value: str) -> bool:
    """Return True if the value points at a secret store instead of a literal.

    Supported reference schemes:
    - ``op://vault/item/field`` — resolved via the 1Password CLI (``op read``).
    - ``env:OTHER_VAR`` — indirection to another environment variable.
    """
    return value.startswith("op://") or value.startswith("env:")


def _read_1password_secret(ref: str) -> str:
    """Resolve an ``op://`` reference using the 1Password CLI.

    Uses ``op read`` with argument-list invocation (no shell) so the reference
    cannot be used for command injection.
    """
    op_path = shutil.which("op")
    if not op_path:
        raise RuntimeError(
            "1Password CLI ('op') not found on PATH; cannot resolve the "
            f"secret reference {ref!r}. Install the 1Password CLI or provide "
            f"the key directly via {API_KEY_ENV}."
        )
    try:
        result = subprocess.run(
            [op_path, "read", ref],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Timed out resolving 1Password secret reference {ref!r}."
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        raise RuntimeError(
            f"Failed to resolve 1Password secret reference {ref!r}: {detail}"
        ) from exc
    return result.stdout.strip()


# Maximum number of chained secret-reference hops (e.g. env: -> env: -> op://)
# before giving up. Guards against runaway or circular references.
_MAX_SECRET_REFERENCE_HOPS = 5


def _resolve_secret_reference_once(value: str) -> str:
    """Resolve a single secret-reference hop, or pass a literal through.

    ``op://`` references are read from 1Password; ``env:VAR`` references read
    another environment variable. Anything else is returned unchanged.
    """
    if value.startswith("op://"):
        return _read_1password_secret(value)
    if value.startswith("env:"):
        var_name = value[len("env:") :].strip()
        resolved = (os.environ.get(var_name) or "").strip()
        if not resolved:
            raise RuntimeError(
                f"Secret reference {value!r} points at environment variable "
                f"{var_name!r}, which is not set."
            )
        return resolved
    return value


def _resolve_secret_reference(value: str) -> str:
    """Resolve a (possibly chained) secret reference to its literal value.

    References may point at other references (e.g. ``env:A`` resolving to
    ``op://...``). Resolution repeats until a literal value is reached, up to
    ``_MAX_SECRET_REFERENCE_HOPS`` hops, raising if the limit is exceeded
    (which also catches circular references such as ``env:A`` -> ``env:A``).
    """
    seen: list[str] = []
    resolved = value
    for _ in range(_MAX_SECRET_REFERENCE_HOPS):
        if not _is_secret_reference(resolved):
            return resolved
        if resolved in seen:
            raise RuntimeError(
                f"Circular secret reference detected while resolving {value!r}."
            )
        seen.append(resolved)
        resolved = _resolve_secret_reference_once(resolved).strip()
    if _is_secret_reference(resolved):
        raise RuntimeError(
            f"Secret reference {value!r} exceeded the maximum of "
            f"{_MAX_SECRET_REFERENCE_HOPS} resolution hops (possible loop)."
        )
    return resolved


def get_probely_api_key(cfg: Dict[str, Any]) -> str:
    """Get the Snyk API & Web API key from env or config.

    Precedence: MCP_SAW_API_KEY env var → saw.api_key → probely.api_key.
    Supports both 'saw' (new) and 'probely' (legacy) config sections.

    The resolved value may be a literal key or a secret reference
    (``op://vault/item/field`` for the 1Password CLI, or ``env:OTHER_VAR``),
    so the key never has to be stored in plaintext in the config file. A
    plaintext key read from the config file is discouraged and logs a warning;
    prefer MCP_SAW_API_KEY or a secret reference.
    """
    key = (os.environ.get(API_KEY_ENV) or "").strip()
    source = "env"
    if not key:
        saw_cfg = cfg.get("saw", {})
        probely_cfg = cfg.get("probely", {})
        key = (
            saw_cfg.get("api_key") or probely_cfg.get("api_key") or ""
        ).strip()
        source = "config"
    if not key or key in _API_KEY_PLACEHOLDERS:
        raise RuntimeError(
            f"Snyk API & Web API key not set. Set {API_KEY_ENV} or update "
            "config/config.yaml 'saw.api_key' / 'probely.api_key'."
        )

    if source == "config" and not _is_secret_reference(key):
        logger.warning(
            "Snyk API & Web API key was loaded as plaintext from the config "
            "file. Prefer %s or a secret reference (e.g. 'op://vault/item/"
            "field') so the key is not stored in plaintext.",
            API_KEY_ENV,
        )

    key = _resolve_secret_reference(key).strip()
    if not key or key in _API_KEY_PLACEHOLDERS:
        raise RuntimeError(
            "Snyk API & Web API key resolved to an empty or placeholder value."
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

    The built-in ``DEFAULT_DISABLED_TOOLS`` are always merged into the blacklist
    so destructive tools stay off unless the operator opts in via the
    ``enabled`` whitelist.
    """
    tools_cfg = cfg.get("tools") or {}

    disabled_tools = list(DEFAULT_DISABLED_TOOLS)
    for name in tools_cfg.get("disabled") or []:
        if name not in disabled_tools:
            disabled_tools.append(name)

    return {
        "enabled_tools": tools_cfg.get("enabled"),  # None means all enabled
        "disabled_tools": disabled_tools,
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
