"""Acceptance tests for scripts/setup-env.sh .env preservation."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from dotenv import dotenv_values

from snyk_apiweb.config import get_probely_api_key, get_probely_base_url

REPO_ROOT = Path(__file__).resolve().parents[1]
SETUP_ENV = REPO_ROOT / "scripts" / "setup-env.sh"

# Dummy keys long enough for get_probely_api_key's short-key warning threshold.
DUMMY_KEY = "dummy-api-key-aaaaaaaa"
DUMMY_KEY_UPDATED = "dummy-api-key-bbbbbbbb"
CUSTOM_BASE = "https://api.staging.example.test"
REPLACED_BASE = "https://api.qa.example.test"


def _prepare_project(tmp_path: Path) -> Path:
    """Layout a throwaway project that runs the real setup-env.sh in isolation."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(SETUP_ENV, scripts / "setup-env.sh")
    return tmp_path


def _run_setup(
    project: Path,
    api_key: str,
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    cmd = ["bash", str(project / "scripts" / "setup-env.sh"), *extra_args]
    return subprocess.run(
        cmd,
        input=api_key + "\n",
        text=True,
        capture_output=True,
        cwd=project,
        check=False,
    )


def _assert_config_reader(
    env_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    expected_key: str,
    expected_base: str | None,
) -> None:
    """Load the written .env the same way the server does, via dotenv + getters."""
    values = dotenv_values(env_path)
    assert values.get("MCP_SAW_API_KEY") == expected_key

    monkeypatch.delenv("MCP_SAW_API_KEY", raising=False)
    monkeypatch.delenv("MCP_SAW_BASE_URL", raising=False)
    for name, value in values.items():
        if name and value is not None:
            monkeypatch.setenv(name, value)

    assert get_probely_api_key({}) == expected_key
    if expected_base is None:
        assert "MCP_SAW_BASE_URL" not in values
        assert get_probely_base_url({}) == "https://api.probely.com"
    else:
        assert values.get("MCP_SAW_BASE_URL") == expected_base
        assert get_probely_base_url({}) == expected_base


def test_creates_env_when_missing(tmp_path, monkeypatch):
    project = _prepare_project(tmp_path)
    result = _run_setup(project, DUMMY_KEY)

    assert result.returncode == 0, result.stderr
    assert DUMMY_KEY not in result.stdout
    assert DUMMY_KEY not in result.stderr
    env_path = project / ".env"
    assert env_path.is_file()
    mode = env_path.stat().st_mode
    assert stat.S_IMODE(mode) == 0o600
    text = env_path.read_text()
    assert text.strip() == f"MCP_SAW_API_KEY={DUMMY_KEY}"
    assert "MCP_SAW_BASE_URL" not in text
    _assert_config_reader(
        env_path, monkeypatch, expected_key=DUMMY_KEY, expected_base=None
    )


def test_updates_existing_api_key(tmp_path, monkeypatch):
    project = _prepare_project(tmp_path)
    env_path = project / ".env"
    env_path.write_text(f"MCP_SAW_API_KEY={DUMMY_KEY}\n")
    os.chmod(env_path, 0o600)

    result = _run_setup(project, DUMMY_KEY_UPDATED)

    assert result.returncode == 0, result.stderr
    assert DUMMY_KEY_UPDATED not in result.stdout
    text = env_path.read_text()
    assert text.count("MCP_SAW_API_KEY=") == 1
    assert f"MCP_SAW_API_KEY={DUMMY_KEY_UPDATED}" in text
    assert DUMMY_KEY not in text
    _assert_config_reader(
        env_path,
        monkeypatch,
        expected_key=DUMMY_KEY_UPDATED,
        expected_base=None,
    )


def test_preserves_unrelated_entries_and_comments(tmp_path, monkeypatch):
    project = _prepare_project(tmp_path)
    env_path = project / ".env"
    env_path.write_text(
        "# keep this comment\n"
        f"MCP_SAW_API_KEY={DUMMY_KEY}\n"
        "MCP_SAW_LOG_LEVEL=DEBUG\n"
        "# trailing note\n"
    )
    os.chmod(env_path, 0o600)

    result = _run_setup(project, DUMMY_KEY_UPDATED)

    assert result.returncode == 0, result.stderr
    text = env_path.read_text()
    assert "# keep this comment\n" in text
    assert "MCP_SAW_LOG_LEVEL=DEBUG\n" in text
    assert "# trailing note\n" in text
    assert text.count("MCP_SAW_API_KEY=") == 1
    assert f"MCP_SAW_API_KEY={DUMMY_KEY_UPDATED}" in text
    values = dotenv_values(env_path)
    assert values.get("MCP_SAW_LOG_LEVEL") == "DEBUG"
    _assert_config_reader(
        env_path,
        monkeypatch,
        expected_key=DUMMY_KEY_UPDATED,
        expected_base=None,
    )


def test_preserves_existing_base_url_when_option_omitted(
    tmp_path, monkeypatch
):
    project = _prepare_project(tmp_path)
    env_path = project / ".env"
    env_path.write_text(
        f"MCP_SAW_API_KEY={DUMMY_KEY}\n"
        f"MCP_SAW_BASE_URL={CUSTOM_BASE}\n"
        "MCP_SAW_LOG_LEVEL=INFO\n"
    )
    os.chmod(env_path, 0o600)

    result = _run_setup(project, DUMMY_KEY_UPDATED)

    assert result.returncode == 0, result.stderr
    text = env_path.read_text()
    assert f"MCP_SAW_BASE_URL={CUSTOM_BASE}" in text
    assert text.count("MCP_SAW_BASE_URL=") == 1
    assert "MCP_SAW_LOG_LEVEL=INFO" in text
    _assert_config_reader(
        env_path,
        monkeypatch,
        expected_key=DUMMY_KEY_UPDATED,
        expected_base=CUSTOM_BASE,
    )


def test_replaces_base_url_when_option_supplied(tmp_path, monkeypatch):
    project = _prepare_project(tmp_path)
    env_path = project / ".env"
    env_path.write_text(
        f"MCP_SAW_API_KEY={DUMMY_KEY}\nMCP_SAW_BASE_URL={CUSTOM_BASE}\n"
    )
    os.chmod(env_path, 0o600)

    result = _run_setup(
        project, DUMMY_KEY_UPDATED, "--base-url", REPLACED_BASE
    )

    assert result.returncode == 0, result.stderr
    text = env_path.read_text()
    assert f"MCP_SAW_BASE_URL={REPLACED_BASE}" in text
    assert CUSTOM_BASE not in text
    assert text.count("MCP_SAW_BASE_URL=") == 1
    assert text.count("MCP_SAW_API_KEY=") == 1
    _assert_config_reader(
        env_path,
        monkeypatch,
        expected_key=DUMMY_KEY_UPDATED,
        expected_base=REPLACED_BASE,
    )


def test_adds_base_url_when_option_supplied_and_missing(tmp_path, monkeypatch):
    project = _prepare_project(tmp_path)
    env_path = project / ".env"
    env_path.write_text(f"MCP_SAW_API_KEY={DUMMY_KEY}\n")
    os.chmod(env_path, 0o600)

    result = _run_setup(project, DUMMY_KEY_UPDATED, "--base-url", CUSTOM_BASE)

    assert result.returncode == 0, result.stderr
    text = env_path.read_text()
    assert f"MCP_SAW_API_KEY={DUMMY_KEY_UPDATED}" in text
    assert f"MCP_SAW_BASE_URL={CUSTOM_BASE}" in text
    assert text.count("MCP_SAW_BASE_URL=") == 1
    _assert_config_reader(
        env_path,
        monkeypatch,
        expected_key=DUMMY_KEY_UPDATED,
        expected_base=CUSTOM_BASE,
    )


def test_collapses_duplicate_managed_keys(tmp_path, monkeypatch):
    project = _prepare_project(tmp_path)
    env_path = project / ".env"
    env_path.write_text(
        f"MCP_SAW_API_KEY={DUMMY_KEY}\n"
        "MCP_SAW_LOG_LEVEL=DEBUG\n"
        f"MCP_SAW_API_KEY={DUMMY_KEY}\n"
        f"MCP_SAW_BASE_URL={CUSTOM_BASE}\n"
        f"MCP_SAW_BASE_URL={CUSTOM_BASE}\n"
    )
    os.chmod(env_path, 0o600)

    result = _run_setup(
        project, DUMMY_KEY_UPDATED, "--base-url", REPLACED_BASE
    )

    assert result.returncode == 0, result.stderr
    text = env_path.read_text()
    assert text.count("MCP_SAW_API_KEY=") == 1
    assert text.count("MCP_SAW_BASE_URL=") == 1
    assert "MCP_SAW_LOG_LEVEL=DEBUG" in text
    _assert_config_reader(
        env_path,
        monkeypatch,
        expected_key=DUMMY_KEY_UPDATED,
        expected_base=REPLACED_BASE,
    )


def test_retains_owner_only_permissions_on_update(tmp_path):
    project = _prepare_project(tmp_path)
    env_path = project / ".env"
    env_path.write_text(f"MCP_SAW_API_KEY={DUMMY_KEY}\n")
    os.chmod(env_path, 0o644)

    result = _run_setup(project, DUMMY_KEY_UPDATED)

    assert result.returncode == 0, result.stderr
    mode = env_path.stat().st_mode
    assert stat.S_IMODE(mode) == 0o600


def test_replaces_export_prefixed_key(tmp_path, monkeypatch):
    project = _prepare_project(tmp_path)
    env_path = project / ".env"
    env_path.write_text(
        f"export MCP_SAW_API_KEY={DUMMY_KEY}\nMCP_SAW_LOG_LEVEL=DEBUG\n"
    )
    os.chmod(env_path, 0o600)

    result = _run_setup(project, DUMMY_KEY_UPDATED)

    assert result.returncode == 0, result.stderr
    text = env_path.read_text()
    assert text.count("MCP_SAW_API_KEY=") == 1
    assert DUMMY_KEY not in text
    assert "MCP_SAW_LOG_LEVEL=DEBUG" in text
    _assert_config_reader(
        env_path,
        monkeypatch,
        expected_key=DUMMY_KEY_UPDATED,
        expected_base=None,
    )


def test_preserves_symlinked_env_and_leaves_no_temp_files(tmp_path):
    project = _prepare_project(tmp_path)
    target = project / "real.env"
    target.write_text(f"MCP_SAW_API_KEY={DUMMY_KEY}\n")
    env_path = project / ".env"
    env_path.symlink_to(target)

    result = _run_setup(project, DUMMY_KEY_UPDATED)

    assert result.returncode == 0, result.stderr
    assert env_path.is_symlink()
    assert f"MCP_SAW_API_KEY={DUMMY_KEY_UPDATED}" in target.read_text()
    assert not list(project.glob(".env.*"))
