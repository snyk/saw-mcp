from __future__ import annotations

import pytest

from snyk_apiweb.config import (
    DEFAULT_DISABLED_TOOLS,
    get_probely_api_key,
    get_probely_base_url,
    get_target_defaults,
    get_tool_filter,
    is_tool_enabled,
    load_config,
)

# --- load_config ---


def test_load_config_from_explicit_path(tmp_config):
    path = tmp_config({"saw": {"api_key": "abc"}})

    result = load_config(path)

    assert result == {"saw": {"api_key": "abc"}}


def test_load_config_resolves_via_saw_env_var(tmp_config, monkeypatch):
    path = tmp_config({"saw": {"base_url": "https://saw.test"}})
    monkeypatch.setenv("MCP_SAW_CONFIG_PATH", path)

    result = load_config()

    assert result["saw"]["base_url"] == "https://saw.test"


def test_load_config_falls_back_to_legacy_env_var(tmp_config, monkeypatch):
    path = tmp_config({"probely": {"api_key": "legacy"}})
    monkeypatch.delenv("MCP_SAW_CONFIG_PATH", raising=False)
    monkeypatch.setenv("MCP_PROBELY_CONFIG_PATH", path)

    result = load_config()

    assert result["probely"]["api_key"] == "legacy"


def test_load_config_returns_empty_dict_for_empty_file(tmp_path):
    cfg = tmp_path / "empty.yaml"
    cfg.write_text("")

    result = load_config(str(cfg))

    assert result == {}


def test_load_config_rejects_path_traversal_via_env(monkeypatch):
    """Path traversal via env var is rejected."""
    monkeypatch.setenv("MCP_SAW_CONFIG_PATH", "/etc/passwd")

    with pytest.raises(
        ValueError, match="resolves outside allowed directories"
    ):
        load_config()


def test_load_config_env_only_returns_empty_when_no_config_file(monkeypatch):
    """When MCP_SAW_API_KEY is set and config file does not exist, return {}."""
    monkeypatch.setenv("MCP_SAW_API_KEY", "env-key")
    monkeypatch.setenv("MCP_SAW_CONFIG_PATH", "/nonexistent/config.yaml")
    monkeypatch.delenv("MCP_PROBELY_CONFIG_PATH", raising=False)

    result = load_config()

    assert result == {}


def test_load_config_env_only_still_loads_when_config_exists(
    tmp_config, monkeypatch
):
    """When MCP_SAW_API_KEY is set but config file exists, load it for target_defaults etc."""
    path = tmp_config({"target_defaults": {"label": "Agentic"}})
    monkeypatch.setenv("MCP_SAW_API_KEY", "env-key")
    monkeypatch.setenv("MCP_SAW_CONFIG_PATH", path)

    result = load_config()

    assert result["target_defaults"]["label"] == "Agentic"


# --- get_probely_base_url ---


def test_get_base_url_prefers_saw_section():
    cfg = {
        "saw": {"base_url": "https://saw.example.com"},
        "probely": {"base_url": "https://probely.example.com"},
    }

    assert get_probely_base_url(cfg) == "https://saw.example.com"


def test_get_base_url_falls_back_to_probely_section():
    cfg = {"probely": {"base_url": "https://probely.example.com"}}

    assert get_probely_base_url(cfg) == "https://probely.example.com"


def test_get_base_url_defaults_when_no_section():
    assert get_probely_base_url({}) == "https://api.probely.com"


# --- get_probely_api_key ---


def test_get_api_key_prefers_env_var_over_config(monkeypatch):
    """MCP_SAW_API_KEY env var takes precedence over config (12-factor)."""
    monkeypatch.setenv("MCP_SAW_API_KEY", "env-key")
    cfg = {"saw": {"api_key": "config-key"}}

    assert get_probely_api_key(cfg) == "env-key"


def test_get_api_key_from_env_when_config_empty(monkeypatch):
    """MCP_SAW_API_KEY allows running without config file."""
    monkeypatch.setenv("MCP_SAW_API_KEY", "env-only-key")

    assert get_probely_api_key({}) == "env-only-key"


def test_get_api_key_prefers_saw_section(monkeypatch):
    """Config is used when env var is not set."""
    monkeypatch.delenv("MCP_SAW_API_KEY", raising=False)
    cfg = {
        "saw": {"api_key": "saw-key"},
        "probely": {"api_key": "probely-key"},
    }

    assert get_probely_api_key(cfg) == "saw-key"


def test_get_api_key_falls_back_to_probely_section(monkeypatch):
    monkeypatch.delenv("MCP_SAW_API_KEY", raising=False)
    cfg = {"probely": {"api_key": "probely-key"}}

    assert get_probely_api_key(cfg) == "probely-key"


def test_get_api_key_raises_when_missing(monkeypatch):
    monkeypatch.delenv("MCP_SAW_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        get_probely_api_key({})


def test_get_api_key_raises_for_saw_placeholder(monkeypatch):
    monkeypatch.delenv("MCP_SAW_API_KEY", raising=False)
    cfg = {"saw": {"api_key": "REPLACE_WITH_YOUR_SAW_API_KEY"}}

    with pytest.raises(RuntimeError):
        get_probely_api_key(cfg)


def test_get_api_key_raises_for_probely_placeholder(monkeypatch):
    monkeypatch.delenv("MCP_SAW_API_KEY", raising=False)
    cfg = {"probely": {"api_key": "REPLACE_WITH_YOUR_PROBELY_API_KEY"}}

    with pytest.raises(RuntimeError):
        get_probely_api_key(cfg)


# --- get_target_defaults ---


def test_target_defaults_returns_label_dict():
    cfg = {"target_defaults": {"label": "Agentic"}}

    result = get_target_defaults(cfg)

    assert result["default_label"] == {"name": "Agentic"}


def test_target_defaults_returns_none_label_when_empty():
    result = get_target_defaults({})

    assert result["default_label"] is None


def test_target_defaults_returns_name_prefix():
    cfg = {"target_defaults": {"name_prefix": "Agentic - "}}

    result = get_target_defaults(cfg)

    assert result["name_prefix"] == "Agentic - "


def test_target_defaults_name_prefix_defaults_to_empty():
    result = get_target_defaults({})

    assert result["name_prefix"] == ""


# --- get_tool_filter / is_tool_enabled ---


def test_tool_filter_whitelist_only():
    cfg = {"tools": {"enabled": ["probely_list_targets"]}}

    result = get_tool_filter(cfg)

    assert result["enabled_tools"] == ["probely_list_targets"]
    # Built-in destructive defaults are always present in the blacklist.
    assert result["disabled_tools"] == DEFAULT_DISABLED_TOOLS


def test_tool_filter_blacklist_merges_with_defaults():
    cfg = {"tools": {"disabled": ["probely_delete_sequence"]}}

    result = get_tool_filter(cfg)

    assert result["enabled_tools"] is None
    assert "probely_delete_sequence" in result["disabled_tools"]
    for tool in DEFAULT_DISABLED_TOOLS:
        assert tool in result["disabled_tools"]


def test_tool_filter_no_config_still_disables_destructive_defaults():
    result = get_tool_filter({})

    assert result["enabled_tools"] is None
    assert result["disabled_tools"] == DEFAULT_DISABLED_TOOLS


def test_tool_filter_does_not_duplicate_default_entries():
    cfg = {"tools": {"disabled": ["probely_delete_target"]}}

    result = get_tool_filter(cfg)

    assert result["disabled_tools"].count("probely_delete_target") == 1


def test_default_disabled_tools_use_real_raw_passthrough_name():
    # The raw passthrough tool is registered as "probelyrequest" (no
    # underscore); the safe default must block that exact name.
    assert "probelyrequest" in DEFAULT_DISABLED_TOOLS
    assert "probely_request" not in DEFAULT_DISABLED_TOOLS


def test_destructive_tools_disabled_by_default_via_is_tool_enabled():
    tf = get_tool_filter({})

    assert is_tool_enabled("probelyrequest", tf) is False
    assert is_tool_enabled("probely_delete_target", tf) is False
    assert is_tool_enabled("probely_delete_credential", tf) is False
    assert is_tool_enabled("probely_bulk_update_findings", tf) is False
    # A normal read tool stays enabled.
    assert is_tool_enabled("probely_list_targets", tf) is True


def test_destructive_tool_opt_in_via_whitelist():
    cfg = {"tools": {"enabled": ["probely_delete_target"]}}
    tf = get_tool_filter(cfg)

    # Whitelist takes precedence, so an explicitly enabled destructive tool runs.
    assert is_tool_enabled("probely_delete_target", tf) is True
    # Everything not on the whitelist stays off.
    assert is_tool_enabled("probelyrequest", tf) is False


def test_is_tool_enabled_whitelist_allows_listed_tool():
    tf = {
        "enabled_tools": ["probely_list_targets"],
        "disabled_tools": [],
    }

    assert is_tool_enabled("probely_list_targets", tf) is True


def test_is_tool_enabled_whitelist_rejects_unlisted_tool():
    tf = {
        "enabled_tools": ["probely_list_targets"],
        "disabled_tools": [],
    }

    assert is_tool_enabled("probely_delete_target", tf) is False


def test_is_tool_enabled_whitelist_takes_precedence_over_blacklist():
    tf = {
        "enabled_tools": ["probely_list_targets"],
        "disabled_tools": ["probely_list_targets"],
    }

    assert is_tool_enabled("probely_list_targets", tf) is True


def test_is_tool_enabled_blacklist_disables_listed_tool():
    tf = {
        "enabled_tools": None,
        "disabled_tools": ["probely_delete_target"],
    }

    assert is_tool_enabled("probely_delete_target", tf) is False


def test_is_tool_enabled_no_filter_means_all_enabled():
    tf = {"enabled_tools": None, "disabled_tools": []}

    assert is_tool_enabled("anything", tf) is True
