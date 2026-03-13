from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Context
from fastmcp.server.elicitation import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
)

from snyk_apiweb.tools import _require_confirmation

# --- Helpers ---


def _make_ctx() -> MagicMock:
    """Build a mock Context."""
    ctx = MagicMock(spec=Context)
    ctx.session = MagicMock()
    ctx.elicit = AsyncMock()
    return ctx


# --- _require_confirmation: elicitation not available ---


class TestRequireConfirmationElicitationUnavailable:
    """When elicitation fails at runtime (exception from ctx.elicit)."""

    def test_auto_approves_when_elicit_raises(self):
        ctx = _make_ctx()
        ctx.elicit.side_effect = Exception("elicitation not available")

        result = asyncio.run(_require_confirmation(ctx, "Confirm?"))

        assert result is True


# --- _require_confirmation: client WITH elicitation ---


class TestRequireConfirmationWithElicitation:
    """When the client supports elicitation (e.g. Cursor IDE)."""

    def test_returns_true_on_user_confirm(self):
        ctx = _make_ctx()
        ctx.elicit.return_value = AcceptedElicitation(data="Confirm")

        result = asyncio.run(_require_confirmation(ctx, "Ready?"))

        assert result is True
        ctx.elicit.assert_awaited_once()

    def test_returns_false_on_user_cancel_choice(self):
        ctx = _make_ctx()
        ctx.elicit.return_value = AcceptedElicitation(data="Cancel")

        result = asyncio.run(_require_confirmation(ctx, "Ready?"))

        assert result is False

    def test_auto_approves_on_declined(self):
        """Decline is a client-level rejection, not a user action."""
        ctx = _make_ctx()
        ctx.elicit.return_value = DeclinedElicitation()

        result = asyncio.run(_require_confirmation(ctx, "Ready?"))

        assert result is True

    def test_auto_approves_on_cancelled(self):
        """Cancel is a client-level rejection, not a user action."""
        ctx = _make_ctx()
        ctx.elicit.return_value = CancelledElicitation()

        result = asyncio.run(_require_confirmation(ctx, "Ready?"))

        assert result is True

    def test_passes_message_and_response_type_to_elicit(self):
        ctx = _make_ctx()
        ctx.elicit.return_value = AcceptedElicitation(data="Confirm")

        asyncio.run(_require_confirmation(ctx, "Deploy to prod?"))

        ctx.elicit.assert_awaited_once_with(
            message="Deploy to prod?",
            response_type=["Confirm", "Cancel"],
        )


# --- register_tool_with_confirmation (via build_server) ---


class TestRegisterToolWithConfirmation:
    """Verify tools registered with confirmation have proper metadata."""

    @pytest.fixture()
    def app(self, monkeypatch):
        monkeypatch.setenv("MCP_SAW_API_KEY", "x" * 32)
        monkeypatch.setenv("MCP_SAW_CONFIG_PATH", "/nonexistent/config.yaml")
        from snyk_apiweb.tools import build_server

        return build_server()

    def test_confirmation_tool_is_registered(self, app):
        tools = asyncio.run(app.list_tools())
        tool_names = {t.name for t in tools}
        assert "probely_update_target" in tool_names

    def test_confirmation_tool_has_title_annotation(self, app):
        tools = asyncio.run(app.list_tools())
        tool = next(t for t in tools if t.name == "probely_update_target")
        assert tool.annotations is not None
        assert tool.annotations.title == "Update Target"

    def test_non_confirmation_tool_has_no_title(self, app):
        tools = asyncio.run(app.list_tools())
        tool = next(t for t in tools if t.name == "probely_list_targets")
        assert (
            tool.annotations is None
            or getattr(tool.annotations, "title", None) is None
        )

    @patch("snyk_apiweb.tools._require_confirmation", new_callable=AsyncMock)
    def test_cancelled_confirmation_returns_cancelled_response(
        self, mock_confirm, app
    ):
        mock_confirm.return_value = False

        result = asyncio.run(
            app.call_tool(
                "probely_update_target", {"targetId": "abc123", "name": "Test"}
            )
        )

        assert any("cancelled" in str(item).lower() for item in result)
        mock_confirm.assert_awaited_once()

    @patch("snyk_apiweb.tools._require_confirmation", new_callable=AsyncMock)
    def test_accepted_confirmation_calls_underlying_function(
        self, mock_confirm, app
    ):
        mock_confirm.return_value = True

        with patch(
            "snyk_apiweb.probely_client.ProbelyClient.update_target",
            return_value={"id": "abc123"},
        ) as mock_api:
            asyncio.run(
                app.call_tool(
                    "probely_update_target",
                    {"targetId": "abc123", "name": "Hello"},
                )
            )
            mock_api.assert_called_once()

    @patch("snyk_apiweb.tools._require_confirmation", new_callable=AsyncMock)
    def test_confirmation_message_uses_message_func(self, mock_confirm, app):
        mock_confirm.return_value = False

        asyncio.run(
            app.call_tool(
                "probely_update_target",
                {"targetId": "abc123", "name": "Hello"},
            )
        )

        confirm_msg = mock_confirm.call_args[0][1]
        assert isinstance(confirm_msg, str)
        assert len(confirm_msg) > 0
