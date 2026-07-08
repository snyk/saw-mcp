"""Lightweight per-tool-call audit trail.

Emits one structured line per MCP tool invocation recording which tool ran,
when, and the result. Lines go to a dedicated ``snyk_apiweb.audit`` logger,
which by default propagates to the root logging configuration (so entries land
in the standard ``saw-mcp.log``). Set ``MCP_SAW_AUDIT_LOG`` to also append the
trail to a dedicated file for persistent, greppable / SIEM-ingestible auditing.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

AUDIT_LOG_ENV = "MCP_SAW_AUDIT_LOG"

audit_logger = logging.getLogger("snyk_apiweb.audit")

_configured = False


def _configure_audit_logger() -> None:
    """Attach a dedicated file handler once if ``MCP_SAW_AUDIT_LOG`` is set."""
    global _configured
    if _configured:
        return
    _configured = True

    audit_logger.setLevel(logging.INFO)

    log_path = os.environ.get(AUDIT_LOG_ENV, "").strip()
    if not log_path:
        return

    target = os.path.abspath(log_path)
    for handler in audit_logger.handlers:
        if (
            isinstance(handler, logging.FileHandler)
            and getattr(handler, "baseFilename", None) == target
        ):
            return

    try:
        file_handler = logging.FileHandler(target, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        audit_logger.addHandler(file_handler)
    except OSError:
        audit_logger.warning(
            "Could not open audit log file %s; falling back to default logging",
            target,
        )


def record_tool_call(
    tool_name: str,
    outcome: str,
    duration_ms: float,
    error: Optional[str] = None,
) -> None:
    """Write a single audit line for one tool invocation.

    Args:
        tool_name: Name of the MCP tool that ran.
        outcome: ``success``, ``api_error`` (API returned an error body), or
            ``error`` (the tool raised an exception).
        duration_ms: Wall-clock duration of the call in milliseconds.
        error: Optional short error summary (exception or API error message).
    """
    _configure_audit_logger()

    fields = [
        f"ts={datetime.now(timezone.utc).isoformat()}",
        f"tool={tool_name}",
        f"outcome={outcome}",
        f"duration_ms={duration_ms:.1f}",
    ]
    if error:
        # Collapse to a single line so each audit entry stays greppable.
        fields.append("error=" + repr(" ".join(str(error).split()))[:500])

    audit_logger.info("audit %s", " ".join(fields))
