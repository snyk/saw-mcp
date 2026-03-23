from __future__ import annotations

import json
from unittest.mock import patch

from snyk_apiweb.probely_client import ProbelyClient

# --- __init__ ---


def test_init_strips_trailing_slash():
    with patch("requests.Session"):
        c = ProbelyClient(base_url="https://api.example.com/", api_key="k")

    assert c.base_url == "https://api.example.com"


def test_init_sets_jwt_authorization_header():
    with patch("requests.Session") as MockSession:
        session = MockSession.return_value
        session.headers = {}
        ProbelyClient(base_url="https://api.example.com", api_key="my-token")

    assert session.headers["Authorization"] == "JWT my-token"
    assert session.headers["Accept"] == "application/json"
    assert session.headers["User-Agent"].startswith("snyk-apiweb-mcp/")


# --- _url ---


def test_url_prepends_slash_if_missing(client):
    assert client._url("targets/") == ("https://api.example.com/targets/")


def test_url_preserves_existing_slash(client):
    assert client._url("/targets/") == ("https://api.example.com/targets/")


# --- request ---


def test_request_returns_status_and_body_for_json(client, mock_response):
    resp = mock_response(
        status_code=200,
        json_data={"id": "t1", "name": "Target"},
        content_type="application/json",
    )
    client._session.request.return_value = resp

    status, body = client.request("GET", "/targets/t1/")

    assert status == 200
    assert body == {"id": "t1", "name": "Target"}


def test_request_wraps_array_response_in_results(client, mock_response):
    resp = mock_response(
        status_code=200,
        json_data=[{"id": "1"}, {"id": "2"}],
        content_type="application/json",
    )
    client._session.request.return_value = resp

    status, body = client.request("GET", "/targets/")

    assert body == {"results": [{"id": "1"}, {"id": "2"}]}


def test_request_returns_raw_for_non_json(client, mock_response):
    resp = mock_response(
        status_code=200,
        text="<html>hello</html>",
        content_type="text/html",
    )
    client._session.request.return_value = resp

    status, body = client.request("GET", "/page")

    assert body == {"raw": "<html>hello</html>"}


def test_request_enriches_body_on_non_ok_status(client, mock_response):
    resp = mock_response(
        status_code=404,
        json_data={"detail": "Not found"},
        content_type="application/json",
        reason="Not Found",
    )
    client._session.request.return_value = resp

    status, body = client.request("GET", "/targets/missing/")

    assert status == 404
    assert body["error"]["status"] == 404
    assert body["error"]["reason"] == "Not Found"
    assert "api.example.com" in body["error"]["url"]


# --- resolve_labels ---


def test_resolve_labels_empty_list(client):
    assert client.resolve_labels([]) == []


def test_resolve_labels_converts_names(client):
    result = client.resolve_labels(["Prod", "Staging"])

    assert result == [{"name": "Prod"}, {"name": "Staging"}]


# --- _build_create_target_payload ---


def test_build_payload_applies_name_prefix(client):
    payload = client._build_create_target_payload(
        name="My App",
        url="https://app.test",
        name_prefix="Agentic - ",
    )

    assert payload["site"]["name"] == "Agentic - My App"


def test_build_payload_merges_labels_with_deduplication(client):
    payload = client._build_create_target_payload(
        name="App",
        url="https://app.test",
        label_names=["Prod", "Agentic"],
        default_label={"name": "Agentic"},
    )

    label_names = [item["name"] for item in payload["labels"]]
    assert label_names == ["Agentic", "Prod"]


def test_build_payload_includes_scanning_agent(client):
    payload = client._build_create_target_payload(
        name="App",
        url="https://app.test",
        scanning_agent_id="agent-1",
    )

    assert payload["scanning_agent"] == {"id": "agent-1"}


def test_build_payload_omits_optional_fields(client):
    payload = client._build_create_target_payload(
        name="App", url="https://app.test"
    )

    assert "labels" not in payload
    assert "scanning_agent" not in payload
    assert "desc" not in payload["site"]


def test_build_payload_includes_desc(client):
    payload = client._build_create_target_payload(
        name="App",
        url="https://app.test",
        desc="A description",
    )

    assert payload["site"]["desc"] == "A description"


# --- create_target ---


def test_create_target_sends_post(client, mock_response):
    resp = mock_response(
        status_code=201,
        json_data={"id": "t1"},
        content_type="application/json",
    )
    client._session.request.return_value = resp

    result = client.create_web_target(name="Web App", url="https://web.test")

    assert result == {"id": "t1"}
    req_call = client._session.request.call_args
    assert req_call.kwargs["method"] == "POST"
    sent_payload = req_call.kwargs["json"]
    assert sent_payload["site"]["name"] == "Web App"
    assert sent_payload["site"]["url"] == "https://web.test"
    assert "collection" not in sent_payload
    assert "schema" not in sent_payload
    assert req_call.kwargs["params"] is None


def test_create_target_can_skip_reachability_check(client, mock_response):
    resp = mock_response(
        status_code=201,
        json_data={"id": "t1"},
        content_type="application/json",
    )
    client._session.request.return_value = resp

    client.create_web_target(
        name="Web App",
        url="https://web.test",
        skip_reachability_check=True,
    )

    req_call = client._session.request.call_args
    assert req_call.kwargs["params"] == {"skip_reachability_check": True}


# --- create_api_target ---


def test_create_api_target_postman_uses_collection_key(client, mock_response):
    resp = mock_response(
        status_code=201,
        json_data={"id": "t2"},
        content_type="application/json",
    )
    client._session.request.return_value = resp
    schema = {"info": {"name": "My API"}, "item": []}

    client.create_api_target(
        name="API",
        target_url="https://api.test",
        schema_type="postman",
        schema=schema,
    )

    sent = client._session.request.call_args.kwargs["json"]
    params = client._session.request.call_args.kwargs["params"]
    assert sent["site"]["api_scan_settings"] == {"api_schema_type": "postman"}
    assert sent["collection"] == schema
    assert "schema" not in sent
    assert params["skip_reachability_check"] is False


def test_create_api_target_openapi_uses_schema_key(client, mock_response):
    resp = mock_response(
        status_code=201,
        json_data={"id": "t3"},
        content_type="application/json",
    )
    client._session.request.return_value = resp
    schema = {"openapi": "3.0.0", "paths": {}}

    client.create_api_target(
        name="API",
        target_url="https://api.test",
        schema_type="openapi",
        schema=schema,
    )

    sent = client._session.request.call_args.kwargs["json"]
    params = client._session.request.call_args.kwargs["params"]
    assert sent["site"]["api_scan_settings"] == {"api_schema_type": "openapi"}
    assert sent["schema"] == schema
    assert "collection" not in sent
    assert params["skip_reachability_check"] is False


def test_create_api_target_openapi_with_url_uses_api_scan_settings(
    client, mock_response
):
    resp = mock_response(
        status_code=201,
        json_data={"id": "t3"},
        content_type="application/json",
    )
    client._session.request.return_value = resp

    client.create_api_target(
        name="API",
        target_url="https://api.test",
        schema_type="openapi",
        schema=None,
        api_schema_url="http://api:8060/",
    )

    sent = client._session.request.call_args.kwargs["json"]
    params = client._session.request.call_args.kwargs["params"]
    assert sent["site"]["api_scan_settings"] == {
        "api_schema_type": "openapi",
        "api_schema_url": "http://api:8060/",
    }
    assert "schema" not in sent
    assert "collection" not in sent
    assert params["skip_reachability_check"] is False


def test_create_api_target_can_skip_reachability_check(client, mock_response):
    resp = mock_response(
        status_code=201,
        json_data={"id": "t4"},
        content_type="application/json",
    )
    client._session.request.return_value = resp
    schema = {"openapi": "3.0.0", "paths": {}}

    client.create_api_target(
        name="API",
        target_url="https://api.test",
        schema_type="openapi",
        schema=schema,
        skip_reachability_check=True,
    )

    params = client._session.request.call_args.kwargs["params"]
    assert params["skip_reachability_check"] is True


# --- _prettyjson_content ---


def test_prettyjson_content_formats_valid_json():
    raw = '{"a":1,"b":2}'

    result = ProbelyClient._prettyjson_content(raw)

    assert result == json.dumps({"a": 1, "b": 2}, indent=2)


def test_prettyjson_content_returns_invalid_string_unchanged():
    raw = "not json {{"

    assert ProbelyClient._prettyjson_content(raw) == raw


# --- configure_form_login ---


def test_configure_form_login_payload(client, mock_response):
    resp = mock_response(
        status_code=200,
        json_data={"id": "t1"},
        content_type="application/json",
    )
    client._session.request.return_value = resp

    client.configure_form_login(
        target_id="t1",
        login_url="https://app.test/login",
        username_field="email",
        password_field="pass",
        username="user@test.com",
        password="s3cret",
        check_pattern="Dashboard",
    )

    sent = client._session.request.call_args.kwargs["json"]
    site = sent["site"]
    assert site["has_form_login"] is True
    assert site["has_sequence_login"] is False
    assert site["form_login_url"] == "https://app.test/login"
    assert site["auth_enabled"] is True
    assert site["form_login_check_pattern"] == "Dashboard"
    assert len(site["form_login"]) == 2


# --- configure_sequence_login ---


def test_configure_sequence_login_enable_disables_form(client, mock_response):
    resp = mock_response(
        status_code=200,
        json_data={"id": "t1"},
        content_type="application/json",
    )
    client._session.request.return_value = resp

    client.configure_sequence_login(target_id="t1", enabled=True)

    sent = client._session.request.call_args.kwargs["json"]
    site = sent["site"]
    assert site["has_sequence_login"] is True
    assert site["has_form_login"] is False
    assert site["auth_enabled"] is True


def test_configure_sequence_login_disable_does_not_touch_form(
    client, mock_response
):
    resp = mock_response(
        status_code=200,
        json_data={"id": "t1"},
        content_type="application/json",
    )
    client._session.request.return_value = resp

    client.configure_sequence_login(target_id="t1", enabled=False)

    sent = client._session.request.call_args.kwargs["json"]
    site = sent["site"]
    assert site["has_sequence_login"] is False
    assert "has_form_login" not in site


# --- configure_logout_detection ---


def test_configure_logout_detection_enable_flow(client, mock_response):
    ok_resp = mock_response(
        status_code=200,
        json_data={"id": "t1"},
        content_type="application/json",
    )
    detectors_resp = mock_response(
        status_code=200,
        json_data={"results": []},
        content_type="application/json",
    )
    client._session.request.side_effect = [
        ok_resp,  # PATCH check_session_url
        detectors_resp,  # GET logout detectors (empty)
        ok_resp,  # POST create logout detector
        ok_resp,  # PATCH enable logout detection
    ]

    client.configure_logout_detection(
        target_id="t1",
        enabled=True,
        check_session_url="https://app.test/api/me",
        logout_detector_type="text",
        logout_detector_value="Login",
    )

    assert client._session.request.call_count == 4


def test_configure_logout_detection_disable_flow(client, mock_response):
    resp = mock_response(
        status_code=200,
        json_data={"id": "t1"},
        content_type="application/json",
    )
    client._session.request.return_value = resp

    client.configure_logout_detection(target_id="t1", enabled=False)

    assert client._session.request.call_count == 1
    sent = client._session.request.call_args.kwargs["json"]
    assert sent["site"]["logout_detection_enabled"] is False


def test_configure_logout_detection_auto_creates_from_sequence(
    client, mock_response
):
    """When no explicit detector is given, extracts CSS from login sequence."""
    ok_resp = mock_response(
        status_code=200,
        json_data={"id": "t1"},
        content_type="application/json",
    )
    empty_detectors = mock_response(
        status_code=200,
        json_data={"results": []},
        content_type="application/json",
    )
    login_steps = json.dumps(
        [
            {
                "type": "fill_value",
                "css": "#username",
                "value": "user",
            },
            {
                "type": "fill_value",
                "css": "#password",
                "value": "pass",
            },
        ]
    )
    sequences_resp = mock_response(
        status_code=200,
        json_data={
            "results": [
                {
                    "type": "login",
                    "enabled": True,
                    "content": login_steps,
                }
            ]
        },
        content_type="application/json",
    )

    client._session.request.side_effect = [
        ok_resp,  # PATCH check_session_url
        empty_detectors,  # GET logout detectors
        sequences_resp,  # GET sequences (for auto-detect)
        ok_resp,  # POST create logout detector
        ok_resp,  # PATCH enable
    ]

    client.configure_logout_detection(
        target_id="t1",
        enabled=True,
        check_session_url="https://app.test/api/me",
    )

    create_detector_call = client._session.request.call_args_list[3]
    sent = create_detector_call.kwargs["json"]
    assert sent["type"] == "sel"
    assert sent["value"] == "#username"


# --- _find_login_sequence_selector ---


def test_find_login_sequence_selector_extracts_css(client, mock_response):
    login_steps = json.dumps(
        [
            {"type": "fill_value", "css": "#email", "value": "x"},
        ]
    )
    resp = mock_response(
        status_code=200,
        json_data={
            "results": [
                {
                    "type": "login",
                    "enabled": True,
                    "content": login_steps,
                }
            ]
        },
        content_type="application/json",
    )
    client._session.request.return_value = resp

    result = client._find_login_sequence_selector("t1")

    assert result == "#email"


def test_find_login_sequence_selector_returns_none_when_empty(
    client, mock_response
):
    resp = mock_response(
        status_code=200,
        json_data={"results": []},
        content_type="application/json",
    )
    client._session.request.return_value = resp

    result = client._find_login_sequence_selector("t1")

    assert result is None
