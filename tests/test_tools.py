from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

import snyk_apiweb.audit as audit
from snyk_apiweb.config import DEFAULT_DISABLED_TOOLS
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


# --- Audit wrapper: safe error summaries ---


def _reset_audit_handlers() -> None:
    audit._configured = False
    for handler in list(audit.audit_logger.handlers):
        audit.audit_logger.removeHandler(handler)
        handler.close()


def test_audit_wrapper_sanitizes_api_error_in_both_sinks(
    tmp_path, monkeypatch, mock_response, caplog
):
    _reset_audit_handlers()
    log_file = tmp_path / "audit.log"
    monkeypatch.setenv(audit.AUDIT_LOG_ENV, str(log_file))
    monkeypatch.setenv("MCP_SAW_API_KEY", "x" * 32)
    monkeypatch.setenv("MCP_SAW_CONFIG_PATH", "/nonexistent/config.yaml")
    monkeypatch.delenv("MCP_PROBELY_CONFIG_PATH", raising=False)
    monkeypatch.delenv("MCP_SAW_BASE_URL", raising=False)

    canary = "synthetic-api-secret-07"
    resp = mock_response(
        status_code=401,
        json_data={"error": {"message": canary}},
        reason="Unauthorized",
    )
    try:
        with patch("requests.Session") as mock_session_cls:
            session = mock_session_cls.return_value
            session.headers = {}
            session.request.return_value = resp

            app = build_server()
            tool = next(
                t
                for t in asyncio.run(app.list_tools())
                if t.name == "probely_list_targets"
            )
            with caplog.at_level(logging.INFO, logger="snyk_apiweb.audit"):
                result = tool.fn()

        assert result["error"]["message"] == canary
        assert result["error"]["status"] == 401
        file_output = log_file.read_text(encoding="utf-8")
        audit_output = "\n".join(
            record.getMessage()
            for record in caplog.records
            if record.name == "snyk_apiweb.audit"
        )
        for sink_output in (audit_output, file_output):
            assert "outcome=api_error" in sink_output
            assert "api_error(status=401)" in sink_output
            assert canary not in sink_output
            assert "Unauthorized" not in sink_output
    finally:
        _reset_audit_handlers()


@pytest.mark.parametrize(
    ("payload", "expected_summary", "canary"),
    [
        (
            {"error": "synthetic-str-error-07"},
            "error='api_error'",
            "synthetic-str-error-07",
        ),
        (
            {"error": ["synthetic-list-error-07"]},
            "error='api_error'",
            "synthetic-list-error-07",
        ),
        (
            {"error": {"status": "synthetic-status-07"}},
            "error='api_error'",
            "synthetic-status-07",
        ),
        (
            {"error": {"status": True, "detail": "synthetic-bool-07"}},
            "error='api_error'",
            "synthetic-bool-07",
        ),
        (
            {"status": 503, "error": "synthetic-top-status-07"},
            "error='api_error(status=503)'",
            "synthetic-top-status-07",
        ),
    ],
)
def test_audit_wrapper_handles_malformed_error_shapes_in_both_sinks(
    tmp_path,
    monkeypatch,
    mock_response,
    caplog,
    payload,
    expected_summary,
    canary,
):
    _reset_audit_handlers()
    log_file = tmp_path / "audit.log"
    monkeypatch.setenv(audit.AUDIT_LOG_ENV, str(log_file))
    monkeypatch.setenv("MCP_SAW_API_KEY", "x" * 32)
    monkeypatch.setenv("MCP_SAW_CONFIG_PATH", "/nonexistent/config.yaml")
    monkeypatch.delenv("MCP_PROBELY_CONFIG_PATH", raising=False)
    monkeypatch.delenv("MCP_SAW_BASE_URL", raising=False)

    resp = mock_response(status_code=200, json_data=payload)
    try:
        with patch("requests.Session") as mock_session_cls:
            session = mock_session_cls.return_value
            session.headers = {}
            session.request.return_value = resp

            app = build_server()
            tool = next(
                t
                for t in asyncio.run(app.list_tools())
                if t.name == "probely_list_targets"
            )
            with caplog.at_level(logging.INFO, logger="snyk_apiweb.audit"):
                result = tool.fn()

        assert result == payload
        file_output = log_file.read_text(encoding="utf-8")
        for sink_output in (caplog.text, file_output):
            assert "outcome=api_error" in sink_output
            assert expected_summary in sink_output
            assert canary not in sink_output
    finally:
        _reset_audit_handlers()


def test_audit_wrapper_sanitizes_exception_in_both_sinks(
    tmp_path, monkeypatch, mock_response, caplog
):
    _reset_audit_handlers()
    log_file = tmp_path / "audit.log"
    monkeypatch.setenv(audit.AUDIT_LOG_ENV, str(log_file))
    monkeypatch.setenv("MCP_SAW_API_KEY", "x" * 32)
    monkeypatch.setenv("MCP_SAW_CONFIG_PATH", "/nonexistent/config.yaml")
    monkeypatch.delenv("MCP_PROBELY_CONFIG_PATH", raising=False)
    monkeypatch.delenv("MCP_SAW_BASE_URL", raising=False)

    plain_canary = "synthetic-runtime-secret-07"
    http_canary = "synthetic-http-secret-07"
    http_exc = requests.HTTPError(
        http_canary, response=mock_response(status_code=403)
    )
    try:
        with patch("requests.Session") as mock_session_cls:
            session = mock_session_cls.return_value
            session.headers = {}
            session.request.side_effect = [
                RuntimeError(plain_canary),
                http_exc,
            ]

            app = build_server()
            tool = next(
                t
                for t in asyncio.run(app.list_tools())
                if t.name == "probely_list_targets"
            )
            with caplog.at_level(logging.INFO, logger="snyk_apiweb.audit"):
                with pytest.raises(RuntimeError, match=plain_canary):
                    tool.fn()
                with pytest.raises(requests.HTTPError, match=http_canary):
                    tool.fn()

        file_output = log_file.read_text(encoding="utf-8")
        for sink_output in (caplog.text, file_output):
            assert "outcome=error" in sink_output
            assert "error='RuntimeError'" in sink_output
            assert "error='HTTPError(status=403)'" in sink_output
            assert plain_canary not in sink_output
            assert http_canary not in sink_output
    finally:
        _reset_audit_handlers()
