from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import yaml

from snyk_apiweb.probely_client import ProbelyClient


@pytest.fixture()
def tmp_config(tmp_path):
    """Factory fixture: write a config dict to a temp YAML file.

    Usage::

        def test_something(tmp_config):
            path = tmp_config({"saw": {"api_key": "k"}})
    """

    def _make(data: dict) -> str:
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump(data))
        return str(cfg)

    return _make


def _build_mock_response(
    status_code=200,
    json_data=None,
    text="",
    content_type="application/json",
    reason="OK",
):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 400
    resp.reason = reason
    resp.text = text
    resp.headers = {"Content-Type": content_type}
    resp.json.return_value = json_data if json_data is not None else {}
    return resp


@pytest.fixture()
def mock_response():
    """Factory fixture to build mock HTTP responses."""
    return _build_mock_response


@pytest.fixture()
def client():
    """ProbelyClient with a mocked session that never hits the network."""
    with patch("requests.Session", autospec=True) as MockSession:
        session_instance = MockSession.return_value
        session_instance.headers = {}
        c = ProbelyClient(
            base_url="https://api.example.com", api_key="test-key"
        )
        c._session = session_instance
        yield c
