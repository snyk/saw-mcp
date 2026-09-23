from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from unittest.mock import patch

from snyk_apiweb import server


def _run_main():
    with (
        patch.object(server, "build_server") as build,
        patch.object(server.logging, "basicConfig") as basic_config,
    ):
        server.main()
    kwargs = basic_config.call_args.kwargs
    for handler in kwargs["handlers"]:
        handler.close()
    return build, kwargs


def test_main_builds_and_runs_server(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    build, _ = _run_main()

    build.assert_called_once_with()
    build.return_value.run.assert_called_once_with()


def test_main_logs_to_rotating_file_in_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    _, kwargs = _run_main()

    file_handlers = [
        h for h in kwargs["handlers"] if isinstance(h, RotatingFileHandler)
    ]
    assert len(file_handlers) == 1
    assert file_handlers[0].baseFilename == str(tmp_path / "saw-mcp.log")


def test_main_honours_log_level_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MCP_SAW_LOG_LEVEL", "debug")

    _, kwargs = _run_main()

    assert kwargs["level"] == logging.DEBUG


def test_main_falls_back_to_info_for_unknown_level(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MCP_SAW_LOG_LEVEL", "chatty")

    _, kwargs = _run_main()

    assert kwargs["level"] == logging.INFO
