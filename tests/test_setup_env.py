"""Acceptance tests for scripts/setup-env.sh .env preservation."""

from __future__ import annotations

import io
import os
import random
import shutil
import stat
import subprocess
import tarfile
from pathlib import Path

import pytest
from dotenv import dotenv_values
from dotenv.parser import parse_stream

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


def _mkproject(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    return project


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


def _fake_mv_that_signals(tmp_path: Path, signal_name: str) -> Path:
    """A `mv` stand-in that signals setup-env.sh and itself, like Ctrl-C."""
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    fake = bin_dir / "mv"
    fake.write_text(
        f"#!/bin/sh\nkill -{signal_name} $PPID\nkill -{signal_name} $$\nsleep 5\nexit 1\n"
    )
    fake.chmod(0o755)
    return bin_dir


@pytest.mark.parametrize("signal_name", ["INT", "TERM", "HUP"])
def test_signal_during_upsert_leaves_no_temp_file(tmp_path, signal_name):
    project = _prepare_project(_mkproject(tmp_path))
    env_path = project / ".env"
    env_path.write_text(f"MCP_SAW_API_KEY={DUMMY_KEY}\n")
    fake_bin = _fake_mv_that_signals(tmp_path, signal_name)

    result = subprocess.run(
        ["bash", str(project / "scripts" / "setup-env.sh")],
        input=DUMMY_KEY_UPDATED + "\n",
        text=True,
        capture_output=True,
        cwd=project,
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        check=False,
    )

    assert result.returncode != 0
    assert not list(project.glob(".env.*"))
    assert DUMMY_KEY_UPDATED not in result.stdout + result.stderr
    assert env_path.read_text() == f"MCP_SAW_API_KEY={DUMMY_KEY}\n"


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root bypasses file permission checks",
)
def test_failed_read_of_existing_env_leaves_no_temp_file(tmp_path):
    project = _prepare_project(tmp_path)
    env_path = project / ".env"
    env_path.write_text(f"MCP_SAW_API_KEY={DUMMY_KEY}\n")
    os.chmod(env_path, 0o000)
    try:
        result = _run_setup(project, DUMMY_KEY_UPDATED)
    finally:
        os.chmod(env_path, 0o600)

    assert result.returncode != 0
    assert not list(project.glob(".env.*"))
    assert DUMMY_KEY_UPDATED not in result.stdout + result.stderr
    assert env_path.read_text() == f"MCP_SAW_API_KEY={DUMMY_KEY}\n"


# A SIGKILL or power loss cannot run the cleanup trap, so a leftover
# `.env.XXXXXX` must still stay out of commits and release tarballs, while the
# committed `.env.example` template must keep being tracked and shipped.
LEFTOVER_TEMP_NAME = ".env.AbC123"
TEMPLATE_NAME = ".env.example"
# Synthetic files that hold (or may hold) a key: always ignored, never shipped.
SENSITIVE_ENV_NAMES = [".env", LEFTOVER_TEMP_NAME, ".env.local", ".env.prod"]


def _git_check_ignore(name: str) -> int:
    return subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "check-ignore",
            "--no-index",
            "-q",
            name,
        ],
        cwd=REPO_ROOT,
        check=False,
    ).returncode


@pytest.mark.parametrize("name", SENSITIVE_ENV_NAMES)
def test_env_files_and_leftover_temp_files_are_gitignored(name):
    assert _git_check_ignore(name) == 0


def test_env_example_template_is_tracked_and_not_ignored():
    tracked = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "ls-files",
            "--error-unmatch",
            TEMPLATE_NAME,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    assert tracked.returncode == 0, "the committed template must stay tracked"
    assert _git_check_ignore(TEMPLATE_NAME) == 1, ".env.example is ignored"


@pytest.mark.skipif(shutil.which("rsync") is None, reason="needs rsync")
def test_release_tarball_ships_template_but_no_env_or_leftover_files(tmp_path):
    template_text = "# synthetic template\nMCP_SAW_API_KEY=\n"
    (tmp_path / "scripts").mkdir()
    (tmp_path / "snyk_apiweb").mkdir()
    shutil.copy(REPO_ROOT / "scripts" / "package.sh", tmp_path / "scripts")
    shutil.copy(
        REPO_ROOT / "snyk_apiweb" / "__init__.py", tmp_path / "snyk_apiweb"
    )
    (tmp_path / TEMPLATE_NAME).write_text(template_text)
    for name in SENSITIVE_ENV_NAMES:
        (tmp_path / name).write_text(f"MCP_SAW_API_KEY={DUMMY_KEY}\n")

    result = subprocess.run(
        ["bash", str(tmp_path / "scripts" / "package.sh")],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    tarball = next((tmp_path / "dist").glob("*.tgz"))
    with tarfile.open(tarball) as tar:
        names = tar.getnames()
        template = tar.extractfile(f"SnykAPIWeb/{TEMPLATE_NAME}")
        shipped_text = template.read().decode() if template else None
    assert any(n.endswith("snyk_apiweb/__init__.py") for n in names)
    assert shipped_text == template_text
    shipped_env_names = sorted(
        Path(n).name for n in names if Path(n).name.startswith(".env")
    )
    assert shipped_env_names == [TEMPLATE_NAME]


# --- Original FRG-160 acceptance: raw-byte preservation and de-duplication ---
#
# Expected files are written out by hand (never produced by the code under test),
# the effective values come from the project's real reader (python-dotenv, as in
# snyk_apiweb.config), and every case asserts the key never reaches stdout/stderr.

NEW_KEY_LINE = f"MCP_SAW_API_KEY={DUMMY_KEY_UPDATED}"
MULTILINE_NOTE = f'NOTE="first\nMCP_SAW_API_KEY={DUMMY_KEY}\nlast"\n'

# (id, initial .env text, extra args, expected .env text)
RAW_BYTE_CASES = [
    (
        "spaces-around-equals",
        f"MCP_SAW_API_KEY = {DUMMY_KEY}\nOTHER=1\n",
        [],
        f"{NEW_KEY_LINE}\nOTHER=1\n",
    ),
    (
        "leading-whitespace",
        f"  MCP_SAW_API_KEY={DUMMY_KEY}\nOTHER=1\n",
        [],
        f"  {NEW_KEY_LINE}\nOTHER=1\n",
    ),
    (
        "tab-indent-and-spaced-equals",
        f"\tMCP_SAW_API_KEY\t=\t{DUMMY_KEY}\nOTHER=1\n",
        [],
        f"\t{NEW_KEY_LINE}\nOTHER=1\n",
    ),
    (
        "export-with-several-spaces",
        f"export   MCP_SAW_API_KEY={DUMMY_KEY}\nOTHER=1\n",
        [],
        f"export   {NEW_KEY_LINE}\nOTHER=1\n",
    ),
    (
        "byte-order-mark",
        f"﻿MCP_SAW_API_KEY={DUMMY_KEY}\nOTHER=1\n",
        [],
        f"﻿{NEW_KEY_LINE}\nOTHER=1\n",
    ),
    (
        "unicode-whitespace-after-export-and-indent",
        f"\u2003export\u00a0MCP_SAW_API_KEY\u3000=\u2009{DUMMY_KEY}\nOTHER=1\n",
        [],
        f"\u2003export\u00a0{NEW_KEY_LINE}\nOTHER=1\n",
    ),
    (
        "quoted-key",
        f"'MCP_SAW_API_KEY'={DUMMY_KEY}\nOTHER=1\n",
        [],
        f"'MCP_SAW_API_KEY'={DUMMY_KEY_UPDATED}\nOTHER=1\n",
    ),
    (
        "multiline-double-quoted-value-mentions-key",
        MULTILINE_NOTE + "OTHER=1\n",
        [],
        MULTILINE_NOTE + "OTHER=1\n" + NEW_KEY_LINE + "\n",
    ),
    (
        "multiline-single-quoted-value-mentions-spaced-export-key",
        f"NOTE='a\nexport MCP_SAW_API_KEY = {DUMMY_KEY}\nb'\nOTHER=1\n",
        [],
        f"NOTE='a\nexport MCP_SAW_API_KEY = {DUMMY_KEY}\nb'\nOTHER=1\n"
        + NEW_KEY_LINE
        + "\n",
    ),
    (
        "escaped-quote-keeps-value-open-across-lines",
        'NOTE="say \\"hi\\"\nMCP_SAW_API_KEY=inner\n"\nOTHER=1\n',
        [],
        'NOTE="say \\"hi\\"\nMCP_SAW_API_KEY=inner\n"\nOTHER=1\n'
        + NEW_KEY_LINE
        + "\n",
    ),
    (
        "real-assignment-around-multiline-value",
        f"MCP_SAW_API_KEY={DUMMY_KEY}\n" + MULTILINE_NOTE,
        [],
        f"{NEW_KEY_LINE}\n" + MULTILINE_NOTE,
    ),
    (
        "unterminated-quote-is-one-bad-line",
        f'BROKEN="oops\nMCP_SAW_API_KEY={DUMMY_KEY}\n',
        [],
        f'BROKEN="oops\n{NEW_KEY_LINE}\n',
    ),
    (
        "comments-and-blank-lines-around-key",
        f"# MCP_SAW_API_KEY={DUMMY_KEY}\n\n#note\nMCP_SAW_API_KEY={DUMMY_KEY}\n\nOTHER=1\n",
        [],
        f"# MCP_SAW_API_KEY={DUMMY_KEY}\n\n#note\n{NEW_KEY_LINE}\n\nOTHER=1\n",
    ),
    (
        "commented-out-key-only-appends",
        f"#MCP_SAW_API_KEY={DUMMY_KEY}\nOTHER=1\n",
        [],
        f"#MCP_SAW_API_KEY={DUMMY_KEY}\nOTHER=1\n{NEW_KEY_LINE}\n",
    ),
    (
        "similar-key-names-are-unrelated",
        f"MCP_SAW_API_KEY_BACKUP={DUMMY_KEY}\nXMCP_SAW_API_KEY=1\n",
        [],
        f"MCP_SAW_API_KEY_BACKUP={DUMMY_KEY}\nXMCP_SAW_API_KEY=1\n{NEW_KEY_LINE}\n",
    ),
    (
        "no-final-newline-after-unrelated-record-appends-on-new-line",
        "OTHER=1",
        [],
        f"OTHER=1\n{NEW_KEY_LINE}\n",
    ),
    (
        "unrelated-last-record-keeps-missing-final-newline",
        f"MCP_SAW_API_KEY={DUMMY_KEY}\nOTHER=1",
        [],
        f"{NEW_KEY_LINE}\nOTHER=1",
    ),
    (
        "managed-last-record-without-newline",
        f"OTHER=1\nMCP_SAW_API_KEY={DUMMY_KEY}",
        [],
        f"OTHER=1\n{NEW_KEY_LINE}\n",
    ),
    (
        "crlf-line-endings-are-kept",
        f"MCP_SAW_API_KEY = {DUMMY_KEY}\r\nOTHER=1\r\n",
        [],
        f"{NEW_KEY_LINE}\r\nOTHER=1\r\n",
    ),
    (
        "mixed-spelling-duplicates-collapse-to-first-position",
        "MCP_SAW_API_KEY=a\nOTHER=1\nexport MCP_SAW_API_KEY = b\n"
        "  MCP_SAW_API_KEY=c\n",
        [],
        f"{NEW_KEY_LINE}\nOTHER=1\n",
    ),
    (
        "base-url-spaced-replaced-and-duplicate-dropped",
        f"MCP_SAW_BASE_URL = {CUSTOM_BASE}\nOTHER=1\nMCP_SAW_BASE_URL={CUSTOM_BASE}\n",
        ["--base-url", REPLACED_BASE],
        f"MCP_SAW_BASE_URL={REPLACED_BASE}\nOTHER=1\n{NEW_KEY_LINE}\n",
    ),
    (
        "base-url-spelled-oddly-is-untouched-when-option-omitted",
        f"export  MCP_SAW_BASE_URL = {CUSTOM_BASE}\nOTHER=1\n",
        [],
        f"export  MCP_SAW_BASE_URL = {CUSTOM_BASE}\nOTHER=1\n{NEW_KEY_LINE}\n",
    ),
]


@pytest.mark.parametrize(
    "initial,args,expected",
    [pytest.param(i, a, e, id=n) for n, i, a, e in RAW_BYTE_CASES],
)
def test_raw_bytes_preserved_and_single_managed_assignment(
    tmp_path, monkeypatch, initial, args, expected
):
    project = _prepare_project(tmp_path)
    env_path = project / ".env"
    env_path.write_bytes(initial.encode())
    os.chmod(env_path, 0o600)

    result = _run_setup(project, DUMMY_KEY_UPDATED, *args)

    assert result.returncode == 0, result.stderr
    assert DUMMY_KEY_UPDATED not in result.stdout + result.stderr
    assert env_path.read_bytes() == expected.encode()
    assert stat.S_IMODE(env_path.stat().st_mode) == 0o600
    expected_base = (
        REPLACED_BASE
        if args
        else CUSTOM_BASE
        if CUSTOM_BASE in initial
        else None
    )
    _assert_config_reader(
        env_path,
        monkeypatch,
        expected_key=DUMMY_KEY_UPDATED,
        expected_base=expected_base,
    )


def test_unrelated_multiline_value_is_read_back_unchanged(
    tmp_path, monkeypatch
):
    project = _prepare_project(tmp_path)
    env_path = project / ".env"
    env_path.write_bytes(MULTILINE_NOTE.encode())

    result = _run_setup(project, DUMMY_KEY_UPDATED)

    assert result.returncode == 0, result.stderr
    values = dotenv_values(env_path)
    assert values["NOTE"] == f"first\nMCP_SAW_API_KEY={DUMMY_KEY}\nlast"
    _assert_config_reader(
        env_path,
        monkeypatch,
        expected_key=DUMMY_KEY_UPDATED,
        expected_base=None,
    )


def test_symlinked_env_with_multiline_value_is_updated_in_place(tmp_path):
    project = _prepare_project(tmp_path)
    target = project / "real.env"
    target.write_bytes(
        (MULTILINE_NOTE + f"MCP_SAW_API_KEY = {DUMMY_KEY}\n").encode()
    )
    env_path = project / ".env"
    env_path.symlink_to(target)

    result = _run_setup(project, DUMMY_KEY_UPDATED)

    assert result.returncode == 0, result.stderr
    assert env_path.is_symlink()
    assert (
        target.read_bytes() == (MULTILINE_NOTE + NEW_KEY_LINE + "\n").encode()
    )
    assert not list(project.glob(".env.*"))


def test_update_needs_no_python_or_third_party_tools(tmp_path):
    """Fresh-install guarantee: only bash and coreutils-style tools are used."""
    tools = ["bash", "mktemp", "cat", "dirname", "chmod", "rm", "mv"]
    paths = {t: shutil.which(t) for t in tools}
    if not all(paths.values()):
        pytest.skip(f"needs {tools} on PATH")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool, path in paths.items():
        (bin_dir / tool).symlink_to(path)
    project = _prepare_project(_mkproject(tmp_path))
    env_path = project / ".env"
    env_path.write_bytes(
        (MULTILINE_NOTE + f"export MCP_SAW_API_KEY = {DUMMY_KEY}\n").encode()
    )

    result = subprocess.run(
        [str(bin_dir / "bash"), str(project / "scripts" / "setup-env.sh")],
        input=DUMMY_KEY_UPDATED + "\n",
        text=True,
        capture_output=True,
        cwd=project,
        env={"PATH": str(bin_dir)},
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (
        env_path.read_bytes()
        == (MULTILINE_NOTE + f"export {NEW_KEY_LINE}\n").encode()
    )


FUZZ_FRAGMENTS = [
    "MCP_SAW_API_KEY=old\n",
    "MCP_SAW_API_KEY = old\n",
    "  MCP_SAW_API_KEY=old # note\n",
    "export  MCP_SAW_API_KEY=old\n",
    "'MCP_SAW_API_KEY'=old\n",
    'MCP_SAW_API_KEY="old"\n',
    "MCP_SAW_API_KEY\n",
    "MCP_SAW_BASE_URL=http://old.example.test\n",
    "\tMCP_SAW_BASE_URL = http://old.example.test\n",
    "OTHER=1\n",
    "OTHER2='x y'\n",
    "# comment MCP_SAW_API_KEY=old\n",
    "#MCP_SAW_API_KEY=old\n",
    "\n",
    "   \n",
    'NOTE="a\nMCP_SAW_API_KEY=old\nb"\n',
    "NOTE='a\nexport MCP_SAW_BASE_URL = old\nb'\n",
    'NOTE="q \\" \nMCP_SAW_API_KEY=old\n"\n',
    'BROKEN="never closed\n',
    "BROKEN2='never closed\n",
    "two words\n",
    "MCP_SAW_API_KEY_X=old\n",
    "=novalue\n",
    "KEY= # only a comment\n",
    "WIN=1\r\n",
    "\u00a0MCP_SAW_API_KEY=old\n",
    "export\u2003MCP_SAW_BASE_URL\u3000=\u2009old\n",
    "\x1cMCP_SAW_API_KEY=old\n",
    "OTHER=caf\u00e9 \u2603\n",
]


@pytest.mark.parametrize("seed", range(120))
def test_random_env_files_match_the_readers_own_records(tmp_path, seed):
    """Other records stay byte-identical and exactly one managed one remains.

    Records and values come from python-dotenv's own parser (the server's
    reader), an implementation independent of the bash scanner under test.
    """
    rng = random.Random(seed)
    parts = [rng.choice(FUZZ_FRAGMENTS) for _ in range(rng.randint(1, 8))]
    if rng.random() < 0.3:
        parts[-1] = parts[-1].rstrip("\r\n")  # missing final newline
    original = ("﻿" if rng.random() < 0.15 else "") + "".join(parts)
    with_base = rng.random() < 0.5
    project = _prepare_project(tmp_path)
    env_path = project / ".env"
    env_path.write_bytes(original.encode())

    args = ["--base-url", REPLACED_BASE] if with_base else []
    result = _run_setup(project, DUMMY_KEY_UPDATED, *args)

    assert result.returncode == 0, result.stderr
    assert DUMMY_KEY_UPDATED not in result.stdout + result.stderr
    managed = {"MCP_SAW_API_KEY"} | (
        {"MCP_SAW_BASE_URL"} if with_base else set()
    )

    def unrelated(text):
        return [
            b.original.string.strip()
            for b in parse_stream(io.StringIO(text))
            if b.key not in managed and b.original.string.strip()
        ]

    final = env_path.read_bytes().decode()
    assert unrelated(final) == unrelated(original)
    bindings = [
        b for b in parse_stream(io.StringIO(final)) if b.key in managed
    ]
    assert sorted(b.key for b in bindings) == sorted(managed)
    values = dotenv_values(env_path)
    assert values["MCP_SAW_API_KEY"] == DUMMY_KEY_UPDATED
    if with_base:
        assert values["MCP_SAW_BASE_URL"] == REPLACED_BASE
