from __future__ import annotations

from unittest.mock import patch

import pytest

from snyk_apiweb.tools import (
    _generate_totp,
    _parse_list_of_dicts,
)

# --- _parse_list_of_dicts ---


def test_parse_returns_none_for_none():
    assert _parse_list_of_dicts(None) is None


def test_parse_returns_list_as_is():
    data = [{"a": 1}, {"b": 2}]

    assert _parse_list_of_dicts(data) is data


def test_parse_json_array_string():
    raw = '[{"name": "Prod"}, {"name": "Dev"}]'

    result = _parse_list_of_dicts(raw)

    assert result == [{"name": "Prod"}, {"name": "Dev"}]


def test_parse_json_object_string_wraps_in_list():
    raw = '{"name": "Solo"}'

    result = _parse_list_of_dicts(raw)

    assert result == [{"name": "Solo"}]


def test_parse_python_repr_string_with_single_quotes():
    raw = "[{'name': 'Prod', 'enabled': True}]"

    result = _parse_list_of_dicts(raw)

    assert result == [{"name": "Prod", "enabled": True}]


def test_parse_wraps_single_dict_in_list():
    data = {"key": "value"}

    result = _parse_list_of_dicts(data)

    assert result == [{"key": "value"}]


def test_parse_raises_for_int():
    with pytest.raises(ValueError, match="Expected a JSON array"):
        _parse_list_of_dicts(42)


def test_parse_raises_for_random_string():
    with pytest.raises(ValueError, match="Expected a JSON array"):
        _parse_list_of_dicts("not valid at all")


# --- _generate_totp ---


@patch("snyk_apiweb.tools.time.time", return_value=1000000000.0)
def test_generate_totp_returns_expected_keys(mock_time):
    result = _generate_totp("JBSWY3DPEHPK3PXP")

    assert set(result.keys()) == {
        "code",
        "remaining_seconds",
        "algorithm",
        "digits",
    }
    assert result["algorithm"] == "SHA1"
    assert result["digits"] == 6


@patch("snyk_apiweb.tools.time.time", return_value=1000000000.0)
def test_generate_totp_code_is_six_digits(mock_time):
    result = _generate_totp("JBSWY3DPEHPK3PXP")

    assert len(result["code"]) == 6
    assert result["code"].isdigit()


@patch("snyk_apiweb.tools.time.time", return_value=1000000000.0)
def test_generate_totp_handles_spaces_and_dashes(mock_time):
    result_clean = _generate_totp("JBSWY3DPEHPK3PXP")
    result_spaces = _generate_totp("JBSW Y3DP EHPK 3PXP")
    result_dashes = _generate_totp("JBSW-Y3DP-EHPK-3PXP")

    assert result_clean["code"] == result_spaces["code"]
    assert result_clean["code"] == result_dashes["code"]


@patch("snyk_apiweb.tools.time.time", return_value=1000000000.0)
def test_generate_totp_sha256_produces_result(mock_time):
    result_sha1 = _generate_totp("JBSWY3DPEHPK3PXP")
    result_sha256 = _generate_totp("JBSWY3DPEHPK3PXP", algorithm="SHA256")

    assert result_sha256["algorithm"] == "SHA256"
    assert len(result_sha256["code"]) == 6
    assert result_sha256["code"] != result_sha1["code"]


@patch("snyk_apiweb.tools.time.time", return_value=1000000000.0)
def test_generate_totp_eight_digits(mock_time):
    result = _generate_totp("JBSWY3DPEHPK3PXP", digits=8)

    assert result["digits"] == 8
    assert len(result["code"]) == 8
    assert result["code"].isdigit()


@patch("snyk_apiweb.tools.time.time", return_value=1000000010.0)
def test_generate_totp_remaining_seconds(mock_time):
    result = _generate_totp("JBSWY3DPEHPK3PXP", period=30)

    assert result["remaining_seconds"] == 10
