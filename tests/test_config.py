from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from snyk_apiweb.config import (
    _is_secret_reference,
    _resolve_secret_reference,
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


def test_get_api_key_raises_for_changeme_placeholder(monkeypatch):
    monkeypatch.delenv("MCP_SAW_API_KEY", raising=False)
    cfg = {"saw": {"api_key": "CHANGEME"}}

    with pytest.raises(RuntimeError):
        get_probely_api_key(cfg)


# --- secret references (op:// / env:) ---


def test_is_secret_reference():
    assert _is_secret_reference("op://vault/item/field") is True
    assert _is_secret_reference("env:MY_KEY") is True
    assert _is_secret_reference("literal-plaintext-key") is False


def test_resolve_env_reference(monkeypatch):
    monkeypatch.setenv("MY_SAW_KEY", "resolved-from-env-var")

    assert (
        _resolve_secret_reference("env:MY_SAW_KEY") == "resolved-from-env-var"
    )


def test_resolve_env_reference_missing_raises(monkeypatch):
    monkeypatch.delenv("MY_SAW_KEY", raising=False)

    with pytest.raises(RuntimeError, match="not set"):
        _resolve_secret_reference("env:MY_SAW_KEY")


def test_resolve_op_reference_uses_1password_cli(monkeypatch):
    monkeypatch.setattr(
        "snyk_apiweb.config.shutil.which", lambda _: "/usr/bin/op"
    )
    run_mock = MagicMock(
        return_value=MagicMock(stdout="op-resolved-secret-value\n")
    )
    monkeypatch.setattr("snyk_apiweb.config.subprocess.run", run_mock)

    result = _resolve_secret_reference("op://vault/saw-mcp/api-key")

    assert result == "op-resolved-secret-value"
    args = run_mock.call_args[0][0]
    assert args == ["/usr/bin/op", "read", "op://vault/saw-mcp/api-key"]


def test_resolve_op_reference_missing_cli_raises(monkeypatch):
    monkeypatch.setattr("snyk_apiweb.config.shutil.which", lambda _: None)

    with pytest.raises(RuntimeError, match="1Password CLI"):
        _resolve_secret_reference("op://vault/saw-mcp/api-key")


def test_resolve_chained_env_to_op_reference(monkeypatch):
    # env:A -> op://... -> literal (multiple hops).
    monkeypatch.setenv("MY_SAW_KEY", "op://vault/saw-mcp/api-key")
    monkeypatch.setattr(
        "snyk_apiweb.config.shutil.which", lambda _: "/usr/bin/op"
    )
    monkeypatch.setattr(
        "snyk_apiweb.config.subprocess.run",
        MagicMock(return_value=MagicMock(stdout="final-literal-secret\n")),
    )

    assert (
        _resolve_secret_reference("env:MY_SAW_KEY") == "final-literal-secret"
    )


def test_resolve_detects_circular_reference(monkeypatch):
    monkeypatch.setenv("MY_SAW_KEY", "env:MY_SAW_KEY")

    with pytest.raises(RuntimeError, match="[Cc]ircular"):
        _resolve_secret_reference("env:MY_SAW_KEY")


def test_get_api_key_resolves_config_op_reference(monkeypatch):
    monkeypatch.delenv("MCP_SAW_API_KEY", raising=False)
    monkeypatch.setattr(
        "snyk_apiweb.config.shutil.which", lambda _: "/usr/bin/op"
    )
    monkeypatch.setattr(
        "snyk_apiweb.config.subprocess.run",
        MagicMock(
            return_value=MagicMock(
                stdout="a-real-looking-api-key-1234567890\n"
            )
        ),
    )
    cfg = {"saw": {"api_key": "op://vault/saw-mcp/api-key"}}

    assert get_probely_api_key(cfg) == "a-real-looking-api-key-1234567890"


def test_get_api_key_plaintext_config_logs_warning(monkeypatch, caplog):
    monkeypatch.delenv("MCP_SAW_API_KEY", raising=False)
    cfg = {"saw": {"api_key": "a-real-looking-api-key-1234567890"}}

    with caplog.at_level("WARNING", logger="snyk_apiweb.config"):
        get_probely_api_key(cfg)

    assert any("plaintext" in r.getMessage() for r in caplog.records)


def test_get_api_key_env_reference_no_plaintext_warning(monkeypatch, caplog):
    monkeypatch.setenv("MCP_SAW_API_KEY", "env:MY_SAW_KEY")
    monkeypatch.setenv("MY_SAW_KEY", "a-real-looking-api-key-1234567890")

    with caplog.at_level("WARNING", logger="snyk_apiweb.config"):
        result = get_probely_api_key({})

    assert result == "a-real-looking-api-key-1234567890"
    assert not any("plaintext" in r.getMessage() for r in caplog.records)


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
