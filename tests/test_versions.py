from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check-versions.py"
_spec = importlib.util.spec_from_file_location("check_versions", _SCRIPT)
check_versions = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_versions)


def test_all_version_declarations_match():
    versions = check_versions.declared_versions()

    assert len(set(versions.values())) == 1, (
        f"Version declarations disagree: {versions}. Bump all of them "
        "together (see AGENTS.md, 'Version bumps and releases')."
    )


def test_check_versions_reports_mismatch_with_expected(capsys):
    assert check_versions.main(["check-versions.py", "0.0.0-nope"]) == 1
    assert "0.0.0-nope" in capsys.readouterr().err
