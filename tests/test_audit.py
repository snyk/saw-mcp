from __future__ import annotations

import logging

import snyk_apiweb.audit as audit
from snyk_apiweb.audit import record_tool_call


def _reset_audit_state():
    """Reset the module-level configuration guard between tests."""
    audit._configured = False
    for handler in list(audit.audit_logger.handlers):
        audit.audit_logger.removeHandler(handler)


def test_record_tool_call_emits_line(caplog):
    _reset_audit_state()
    with caplog.at_level(logging.INFO, logger="snyk_apiweb.audit"):
        record_tool_call("probely_list_targets", "success", 12.3)

    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "tool=probely_list_targets" in message
    assert "outcome=success" in message
    assert "duration_ms=12.3" in message
    assert "ts=" in message


def test_record_tool_call_includes_error(caplog):
    _reset_audit_state()
    with caplog.at_level(logging.INFO, logger="snyk_apiweb.audit"):
        record_tool_call(
            "probely_delete_target",
            "error",
            5.0,
            error="ValueError: boom",
        )

    message = caplog.records[0].getMessage()
    assert "outcome=error" in message
    assert "boom" in message


def test_record_tool_call_writes_to_file_when_env_set(tmp_path, monkeypatch):
    _reset_audit_state()
    log_file = tmp_path / "audit.log"
    monkeypatch.setenv(audit.AUDIT_LOG_ENV, str(log_file))

    record_tool_call("probely_get_target", "success", 1.0)

    contents = log_file.read_text()
    assert "tool=probely_get_target" in contents
    assert "outcome=success" in contents
    _reset_audit_state()
