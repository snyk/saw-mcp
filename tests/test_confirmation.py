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
from mcp.types import (
    ClientCapabilities,
    ElicitationCapability,
    FormElicitationCapability,
)

from snyk_apiweb.tools import _require_confirmation

# --- Helpers ---


def _make_ctx(*, supports_elicitation: bool = True) -> MagicMock:
    """Build a mock Context with configurable elicitation support."""
    ctx = MagicMock(spec=Context)
    ctx.session = MagicMock()
    ctx.session.check_client_capability.return_value = supports_elicitation
    ctx.elicit = AsyncMock()
    return ctx


# --- _require_confirmation: client WITHOUT elicitation ---


class TestRequireConfirmationWithoutElicitation:
    """When the client does NOT support elicitation (e.g. CLI clients)."""

    def test_returns_true_without_calling_elicit(self):
        ctx = _make_ctx(supports_elicitation=False)

        result = asyncio.run(_require_confirmation(ctx, "Confirm?"))

        assert result is True
        ctx.elicit.assert_not_called()

    def test_checks_form_elicitation_capability(self):
        ctx = _make_ctx(supports_elicitation=False)

        asyncio.run(_require_confirmation(ctx, "Confirm?"))

        ctx.session.check_client_capability.assert_called_once()
        cap = ctx.session.check_client_capability.call_args[0][0]
        assert isinstance(cap, ClientCapabilities)
        assert isinstance(cap.elicitation, ElicitationCapability)
        assert isinstance(cap.elicitation.form, FormElicitationCapability)


# --- _require_confirmation: client WITH elicitation ---


class TestRequireConfirmationWithElicitation:
    """When the client supports elicitation (e.g. Cursor IDE)."""

    def test_returns_true_on_user_confirm(self):
        ctx = _make_ctx(supports_elicitation=True)
        ctx.elicit.return_value = AcceptedElicitation(data="Confirm")

        result = asyncio.run(_require_confirmation(ctx, "Ready?"))

        assert result is True
        ctx.elicit.assert_awaited_once()

    def test_returns_false_on_user_cancel_choice(self):
        ctx = _make_ctx(supports_elicitation=True)
        ctx.elicit.return_value = AcceptedElicitation(data="Cancel")

        result = asyncio.run(_require_confirmation(ctx, "Ready?"))

        assert result is False

    def test_returns_false_on_declined(self):
        ctx = _make_ctx(supports_elicitation=True)
        ctx.elicit.return_value = DeclinedElicitation()

        result = asyncio.run(_require_confirmation(ctx, "Ready?"))

        assert result is False

    def test_returns_false_on_cancelled(self):
        ctx = _make_ctx(supports_elicitation=True)
        ctx.elicit.return_value = CancelledElicitation()

        result = asyncio.run(_require_confirmation(ctx, "Ready?"))

        assert result is False

    def test_passes_message_and_response_type_to_elicit(self):
        ctx = _make_ctx(supports_elicitation=True)
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
