from __future__ import annotations

import asyncio
import re
from pathlib import Path
from unittest.mock import create_autospec, patch

import pytest

from snyk_apiweb.config import DEFAULT_DISABLED_TOOLS
from snyk_apiweb.probely_client import ProbelyClient
from snyk_apiweb.tools import (
    _MAX_PARSE_INPUT_LEN,
    UnsafeURLError,
    _assert_url_is_safe,
    _generate_totp,
    _parse_list_of_dicts,
    _safe_get,
    build_server,
)

# --- _parse_list_of_dicts ---


def test_parse_returns_none_for_none():
    assert _parse_list_of_dicts(None) is None


def test_parse_returns_list_as_is():
    data = [{"a": 1}, {"b": 2}]

    assert _parse_list_of_dicts(data) is data


def test_parse_json_array_string():
    raw = '[{"name": "Prod"}, {"name": "Dev"}]'

    result = _parse_list_of_dicts(raw)

    assert result == [{"name": "Prod"}, {"name": "Dev"}]


def test_parse_json_object_string_wraps_in_list():
    raw = '{"name": "Solo"}'

    result = _parse_list_of_dicts(raw)

    assert result == [{"name": "Solo"}]


def test_parse_python_repr_string_with_single_quotes():
    raw = "[{'name': 'Prod', 'enabled': True}]"

    result = _parse_list_of_dicts(raw)

    assert result == [{"name": "Prod", "enabled": True}]


def test_parse_wraps_single_dict_in_list():
    data = {"key": "value"}

    result = _parse_list_of_dicts(data)

    assert result == [{"key": "value"}]


def test_parse_raises_for_int():
    with pytest.raises(ValueError, match="Expected a JSON array"):
        _parse_list_of_dicts(42)


def test_parse_raises_for_random_string():
    with pytest.raises(ValueError, match="Expected a JSON array"):
        _parse_list_of_dicts("not valid at all")


def test_parse_raises_for_oversized_string():
    oversized = "[" + ("0," * _MAX_PARSE_INPUT_LEN) + "0]"

    with pytest.raises(ValueError, match="Input too large"):
        _parse_list_of_dicts(oversized)


def test_parse_accepts_string_at_size_limit():
    # A valid JSON array padded with whitespace to exactly the limit still parses.
    base = '[{"name": "Prod"}]'
    raw = base + " " * (_MAX_PARSE_INPUT_LEN - len(base))

    assert len(raw) == _MAX_PARSE_INPUT_LEN
    assert _parse_list_of_dicts(raw) == [{"name": "Prod"}]


# --- _generate_totp ---


@patch("snyk_apiweb.tools.time.time", return_value=1000000000.0)
def test_generate_totp_returns_expected_keys(mock_time):
    result = _generate_totp("JBSWY3DPEHPK3PXP")

    assert set(result.keys()) == {
        "code",
        "remaining_seconds",
        "algorithm",
        "digits",
    }
    assert result["algorithm"] == "SHA1"
    assert result["digits"] == 6


@patch("snyk_apiweb.tools.time.time", return_value=1000000000.0)
def test_generate_totp_code_is_six_digits(mock_time):
    result = _generate_totp("JBSWY3DPEHPK3PXP")

    assert len(result["code"]) == 6
    assert result["code"].isdigit()


@patch("snyk_apiweb.tools.time.time", return_value=1000000000.0)
def test_generate_totp_handles_spaces_and_dashes(mock_time):
    result_clean = _generate_totp("JBSWY3DPEHPK3PXP")
    result_spaces = _generate_totp("JBSW Y3DP EHPK 3PXP")
    result_dashes = _generate_totp("JBSW-Y3DP-EHPK-3PXP")

    assert result_clean["code"] == result_spaces["code"]
    assert result_clean["code"] == result_dashes["code"]


@patch("snyk_apiweb.tools.time.time", return_value=1000000000.0)
def test_generate_totp_sha256_produces_result(mock_time):
    result_sha1 = _generate_totp("JBSWY3DPEHPK3PXP")
    result_sha256 = _generate_totp("JBSWY3DPEHPK3PXP", algorithm="SHA256")

    assert result_sha256["algorithm"] == "SHA256"
    assert len(result_sha256["code"]) == 6
    assert result_sha256["code"] != result_sha1["code"]


@patch("snyk_apiweb.tools.time.time", return_value=1000000000.0)
def test_generate_totp_eight_digits(mock_time):
    result = _generate_totp("JBSWY3DPEHPK3PXP", digits=8)

    assert result["digits"] == 8
    assert len(result["code"]) == 8
    assert result["code"].isdigit()


@patch("snyk_apiweb.tools.time.time", return_value=1000000010.0)
def test_generate_totp_remaining_seconds(mock_time):
    result = _generate_totp("JBSWY3DPEHPK3PXP", period=30)

    assert result["remaining_seconds"] == 10


def test_build_server_registers_prompts(monkeypatch):
    monkeypatch.setenv("MCP_SAW_API_KEY", "x" * 32)
    monkeypatch.setenv("MCP_SAW_CONFIG_PATH", "/nonexistent/config.yaml")

    app = build_server()
    prompts = asyncio.run(app.list_prompts())
    prompt_names = {prompt.name for prompt in prompts}

    assert "saw_web_target_configuration" in prompt_names
    assert "saw_api_target_configuration" in prompt_names


def test_build_server_disables_destructive_tools_by_default(monkeypatch):
    monkeypatch.setenv("MCP_SAW_API_KEY", "x" * 32)
    monkeypatch.setenv("MCP_SAW_CONFIG_PATH", "/nonexistent/config.yaml")

    app = build_server()
    tool_names = {tool.name for tool in asyncio.run(app.list_tools())}

    # Destructive tools are off by default (env-only mode, no config file).
    assert "probelyrequest" not in tool_names
    assert "probely_delete_target" not in tool_names
    assert "probely_delete_credential" not in tool_names
    assert "probely_bulk_update_findings" not in tool_names
    # Ordinary read tools remain available.
    assert "probely_list_targets" in tool_names


def test_shipped_config_files_list_only_real_tool_names(monkeypatch):
    monkeypatch.setenv("MCP_SAW_API_KEY", "x" * 32)
    monkeypatch.setenv("MCP_SAW_CONFIG_PATH", "/nonexistent/config.yaml")

    config_dir = Path(__file__).resolve().parents[1] / "config"
    listed = set()
    for name in ("config.yaml.dist", "saw_rules.mdc"):
        text = (config_dir / name).read_text()
        listed |= set(re.findall(r"\bprobely_[a-z0-9]+[a-z0-9_]*\b", text))
    assert listed, "no tool names found in the shipped config files"

    app = build_server()
    # Destructive tools are absent from a default build but are still real.
    registered = {tool.name for tool in asyncio.run(app.list_tools())} | set(
        DEFAULT_DISABLED_TOOLS
    )

    unknown = sorted(listed - registered)
    assert not unknown, (
        "config/config.yaml.dist lists tool names that are not registered: "
        f"{unknown}. Tool names are matched exactly, so a stale entry has no "
        "effect. Update config.yaml.dist and saw_rules.mdc when renaming a tool."
    )


# --- probely_update_target ---


@pytest.fixture()
def mock_server(monkeypatch):
    """Build the server around an autospec'd ProbelyClient."""
    monkeypatch.setenv("MCP_SAW_API_KEY", "x" * 32)
    monkeypatch.setenv("MCP_SAW_CONFIG_PATH", "/nonexistent/config.yaml")
    mock_client = create_autospec(ProbelyClient, instance=True)
    mock_client.update_target.return_value = {"id": "t1"}
    mock_client.resolve_labels.side_effect = lambda names: [
        {"name": n} for n in names
    ]
    with patch("snyk_apiweb.tools.ProbelyClient", return_value=mock_client):
        app = build_server()
    return app, mock_client


def _update_target(app, **args):
    tool = asyncio.run(app.get_tool("probely_update_target"))
    return asyncio.run(tool.run({"targetId": "t1", **args}))


def test_update_target_basic_auth_sets_site_fields(mock_server):
    app, mock_client = mock_server

    _update_target(
        app,
        basic_auth_username="credentials://u",
        basic_auth_password="credentials://p",
    )

    site = mock_client.update_target.call_args.kwargs["site"]
    assert site["has_basic_auth"] is True
    assert site["basic_auth"] == {
        "username": "credentials://u",
        "password": "credentials://p",
    }


def test_update_target_basic_auth_requires_both_fields(mock_server):
    app, mock_client = mock_server

    result = _update_target(app, basic_auth_username="api-user")

    assert "error" in result.structured_content
    mock_client.update_target.assert_not_called()


def test_update_target_api_auth_headers_enable_api_login(mock_server):
    app, mock_client = mock_server
    header = {
        "name": "X-API-Key",
        "value": "credentials://k",
        "value_is_sensitive": False,
        "allow_testing": False,
        "authentication": True,
        "authentication_secondary": False,
    }

    _update_target(app, api_auth_headers=[header])

    site = mock_client.update_target.call_args.kwargs["site"]
    assert site["headers"] == [header]
    assert site["api_scan_settings"] == {
        "api_login_enabled": True,
        "api_headers_cookies_login_enabled_secondary": False,
        "api_login_method": "headers_or_cookies",
    }


def test_update_target_plain_headers_do_not_enable_api_login(mock_server):
    app, mock_client = mock_server

    _update_target(app, headers=[{"name": "X-Env", "value": "staging"}])

    site = mock_client.update_target.call_args.kwargs["site"]
    assert site["headers"] == [{"name": "X-Env", "value": "staging"}]
    assert "api_scan_settings" not in site


def test_update_target_empty_scanning_agent_removes_it(mock_server):
    app, mock_client = mock_server

    _update_target(app, scanning_agent_id="")

    assert mock_client.update_target.call_args.kwargs["scanning_agent"] is None


def test_update_target_labels_and_name(mock_server):
    app, mock_client = mock_server

    _update_target(app, name="Shop", labels=["Production"])

    kwargs = mock_client.update_target.call_args.kwargs
    assert kwargs["site"] == {"name": "Shop"}
    assert kwargs["labels"] == [{"name": "Production"}]


# --- register_tool audit wrapper ---


def test_tool_exception_is_audited_and_reraised(mock_server):
    app, mock_client = mock_server
    mock_client.get_target.side_effect = RuntimeError("boom")
    tool = asyncio.run(app.get_tool("probely_get_target"))

    with (
        patch("snyk_apiweb.tools.record_tool_call") as record,
        pytest.raises(RuntimeError, match="boom"),
    ):
        asyncio.run(tool.run({"targetId": "t1"}))

    tool_name, outcome, _duration, error = record.call_args.args
    assert (tool_name, outcome) == ("probely_get_target", "error")
    assert error == "RuntimeError: boom"


# --- SSRF protection: _assert_url_is_safe ---


def test_assert_url_rejects_non_https():
    with pytest.raises(UnsafeURLError, match="https"):
        _assert_url_is_safe("http://example.com/schema.json")


def test_assert_url_rejects_file_scheme():
    with pytest.raises(UnsafeURLError, match="https"):
        _assert_url_is_safe("file:///etc/passwd")


def test_assert_url_rejects_missing_hostname():
    with pytest.raises(UnsafeURLError, match="hostname"):
        _assert_url_is_safe("https:///no-host")


def test_assert_url_rejects_aws_metadata_endpoint():
    with pytest.raises(UnsafeURLError, match="non-public"):
        _assert_url_is_safe("https://169.254.169.254/latest/meta-data/")


def test_assert_url_rejects_localhost_ip():
    with pytest.raises(UnsafeURLError, match="non-public"):
        _assert_url_is_safe("https://127.0.0.1/schema.json")


def test_assert_url_rejects_private_ip():
    with pytest.raises(UnsafeURLError, match="non-public"):
        _assert_url_is_safe("https://10.0.0.5/schema.json")
    with pytest.raises(UnsafeURLError, match="non-public"):
        _assert_url_is_safe("https://192.168.1.10/schema.json")
    with pytest.raises(UnsafeURLError, match="non-public"):
        _assert_url_is_safe("https://172.16.0.1/schema.json")


def test_assert_url_rejects_ipv4_mapped_ipv6_metadata():
    with pytest.raises(UnsafeURLError, match="non-public"):
        _assert_url_is_safe("https://[::ffff:169.254.169.254]/latest/")


def test_assert_url_rejects_hostname_resolving_to_private(monkeypatch):
    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(2, 1, 6, "", ("10.0.0.5", port or 443))]

    monkeypatch.setattr(
        "snyk_apiweb.tools.socket.getaddrinfo", fake_getaddrinfo
    )
    with pytest.raises(UnsafeURLError, match="non-public"):
        _assert_url_is_safe("https://internal.evil.example/schema.json")


def test_assert_url_rejects_unresolvable_host(monkeypatch):
    import socket as _socket

    def fake_getaddrinfo(host, port, *args, **kwargs):
        raise _socket.gaierror("nodename nor servname provided")

    monkeypatch.setattr(
        "snyk_apiweb.tools.socket.getaddrinfo", fake_getaddrinfo
    )
    with pytest.raises(UnsafeURLError, match="resolve"):
        _assert_url_is_safe("https://does-not-exist.example/schema.json")


def test_assert_url_allows_public_host(monkeypatch):
    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(2, 1, 6, "", ("93.184.216.34", port or 443))]

    monkeypatch.setattr(
        "snyk_apiweb.tools.socket.getaddrinfo", fake_getaddrinfo
    )
    # Should not raise for a public address.
    _assert_url_is_safe("https://example.com/schema.json")


def test_assert_url_allowlist_blocks_unlisted_host(monkeypatch):
    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(2, 1, 6, "", ("93.184.216.34", port or 443))]

    monkeypatch.setattr(
        "snyk_apiweb.tools.socket.getaddrinfo", fake_getaddrinfo
    )
    with pytest.raises(UnsafeURLError, match="allow-list"):
        _assert_url_is_safe(
            "https://example.com/schema.json",
            allowlist=["trusted.example"],
        )


def test_assert_url_allowlist_permits_subdomain(monkeypatch):
    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(2, 1, 6, "", ("93.184.216.34", port or 443))]

    monkeypatch.setattr(
        "snyk_apiweb.tools.socket.getaddrinfo", fake_getaddrinfo
    )
    _assert_url_is_safe(
        "https://raw.trusted.example/schema.json",
        allowlist=["trusted.example"],
    )


# --- SSRF protection: _safe_get redirect handling ---


class _FakeResponse:
    def __init__(self, status_code, headers=None):
        self.status_code = status_code
        self.headers = headers or {}

    @property
    def is_redirect(self):
        return self.status_code in (301, 302, 303, 307, 308)

    @property
    def is_permanent_redirect(self):
        return self.status_code in (308,)

    def raise_for_status(self):
        return None


def test_safe_get_revalidates_redirect_target(monkeypatch):
    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(2, 1, 6, "", ("93.184.216.34", port or 443))]

    monkeypatch.setattr(
        "snyk_apiweb.tools.socket.getaddrinfo", fake_getaddrinfo
    )

    # First hop redirects to the AWS metadata endpoint, which must be blocked
    # when _safe_get re-validates the redirect target.
    def fake_get(url, timeout=60, allow_redirects=False):
        return _FakeResponse(
            302, {"Location": "https://169.254.169.254/latest/meta-data/"}
        )

    monkeypatch.setattr("requests.get", fake_get)
    with pytest.raises(UnsafeURLError, match="non-public"):
        _safe_get("https://example.com/schema.json")


def test_safe_get_returns_ok_response(monkeypatch):
    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(2, 1, 6, "", ("93.184.216.34", port or 443))]

    monkeypatch.setattr(
        "snyk_apiweb.tools.socket.getaddrinfo", fake_getaddrinfo
    )

    ok = _FakeResponse(200, {"Content-Type": "application/json"})

    def fake_get(url, timeout=60, allow_redirects=False):
        return ok

    monkeypatch.setattr("requests.get", fake_get)
    assert _safe_get("https://example.com/schema.json") is ok
