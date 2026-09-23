#!/usr/bin/env python3
"""Check that every version declaration in the repo agrees.

Usage: scripts/check-versions.py [EXPECTED_VERSION]

With EXPECTED_VERSION (e.g. from a release tag), every declaration must also
equal it. Exits non-zero and lists the mismatches otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _regex(path: str, pattern: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        raise SystemExit(f"Could not find a version in {path}")
    return match.group(1)


def declared_versions() -> dict[str, str]:
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    plugin = json.loads(
        (ROOT / ".cursor-plugin/plugin.json").read_text(encoding="utf-8")
    )
    return {
        "snyk_apiweb/__init__.py __version__": _regex(
            "snyk_apiweb/__init__.py", r'^__version__\s*=\s*"([^"]+)"'
        ),
        "pyproject.toml project.version": _regex(
            "pyproject.toml", r'^version\s*=\s*"([^"]+)"'
        ),
        "server.json version": server["version"],
        "server.json packages[0].version": server["packages"][0]["version"],
        ".cursor-plugin/plugin.json version": plugin["version"],
    }


def main(argv: list[str]) -> int:
    versions = declared_versions()
    expected = argv[1] if len(argv) > 1 else None
    if expected is None and len(set(versions.values())) == 1:
        print(
            f"All version declarations match: {next(iter(versions.values()))}"
        )
        return 0
    if expected is not None and set(versions.values()) == {expected}:
        print(f"All version declarations match {expected}")
        return 0

    print("Version declarations do not match:", file=sys.stderr)
    if expected is not None:
        print(f"  expected: {expected}", file=sys.stderr)
    for where, version in versions.items():
        print(f"  {version:<10} {where}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
