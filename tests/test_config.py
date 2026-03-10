from __future__ import annotations

import pytest

from snyk_apiweb.config import (
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


def test_get_api_key_prefers_saw_section():
    cfg = {
        "saw": {"api_key": "saw-key"},
        "probely": {"api_key": "probely-key"},
    }

    assert get_probely_api_key(cfg) == "saw-key"


def test_get_api_key_falls_back_to_probely_section():
    cfg = {"probely": {"api_key": "probely-key"}}

    assert get_probely_api_key(cfg) == "probely-key"


def test_get_api_key_raises_when_missing():
    with pytest.raises(RuntimeError):
        get_probely_api_key({})


def test_get_api_key_raises_for_saw_placeholder():
    cfg = {"saw": {"api_key": "REPLACE_WITH_YOUR_SAW_API_KEY"}}

    with pytest.raises(RuntimeError):
        get_probely_api_key(cfg)


def test_get_api_key_raises_for_probely_placeholder():
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
    assert result["disabled_tools"] == []


def test_tool_filter_blacklist_only():
    cfg = {"tools": {"disabled": ["probely_delete_target"]}}

    result = get_tool_filter(cfg)

    assert result["enabled_tools"] is None
    assert result["disabled_tools"] == ["probely_delete_target"]


def test_tool_filter_no_config():
    result = get_tool_filter({})

    assert result["enabled_tools"] is None
    assert result["disabled_tools"] == []


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
