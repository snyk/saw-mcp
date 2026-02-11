from __future__ import annotations
import json as _json
import hmac as _hmac
import hashlib as _hashlib
import struct as _struct
import time as _time
import base64 as _base64
import re as _re
from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from fastmcp import FastMCP
from .probely_client import ProbelyClient
from .config import load_config, get_probely_api_key, get_probely_base_url, get_tool_filter, get_target_defaults, is_tool_enabled


def _parse_list_of_dicts(value: Any) -> Optional[List[Dict[str, Any]]]:
    """Parse a value that should be a list of dicts.

    MCP tool parameters with complex types (e.g. list[Dict[str, Any]]) are
    sometimes delivered as JSON strings instead of native Python objects because
    of how ``from __future__ import annotations`` interacts with FastMCP/Pydantic
    schema generation.  This helper normalises both representations so that tool
    functions always receive a proper ``list[dict]`` (or ``None``).
    """
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        # Try standard JSON first
        try:
            parsed = _json.loads(value)
            if isinstance(parsed, list):
                return parsed
            # Single object → wrap in a list
            if isinstance(parsed, dict):
                return [parsed]
        except (_json.JSONDecodeError, TypeError):
            pass
        # Fallback: MCP frameworks may deliver Python-repr strings (single
        # quotes, True/False instead of true/false).  Try ast.literal_eval.
        import ast as _ast
        try:
            parsed = _ast.literal_eval(value)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
        except (ValueError, SyntaxError):
            pass
    # Single dict passed as a native object → wrap in a list
    if isinstance(value, dict):
        return [value]
    raise ValueError(f"Expected a JSON array (list of objects), got: {type(value).__name__}. Value: {repr(value)[:200]}")


def _generate_totp(secret: str, algorithm: str = "SHA1", digits: int = 6, period: int = 30) -> Dict[str, Any]:
    """Generate a TOTP code from a base32 secret.

    Returns dict with ``code``, ``remaining_seconds``, ``algorithm``, and ``digits``.
    """
    clean = _re.sub(r'[\s-]', '', secret).upper()
    padding = (8 - len(clean) % 8) % 8
    key = _base64.b32decode(clean + '=' * padding)

    hash_func = getattr(_hashlib, algorithm.lower(), _hashlib.sha1)
    now = int(_time.time())
    counter = now // period
    remaining = period - (now % period)

    msg = _struct.pack('>Q', counter)
    mac = _hmac.new(key, msg, hash_func).digest()
    offset = mac[-1] & 0x0F
    code_int = _struct.unpack('>I', mac[offset:offset + 4])[0] & 0x7FFFFFFF
    code = str(code_int % (10 ** digits)).zfill(digits)

    return {"code": code, "remaining_seconds": remaining, "algorithm": algorithm, "digits": digits}


def build_server() -> FastMCP:
    cfg = load_config()
    base_url = get_probely_base_url(cfg)
    api_key = get_probely_api_key(cfg)
    client = ProbelyClient(base_url=base_url, api_key=api_key)
    tool_filter = get_tool_filter(cfg)
    target_defaults = get_target_defaults(cfg)

    app = FastMCP(cfg.get("server", {}).get("name", "Snyk APIWeb"))

    def register_tool(name: str) -> Callable:
        """Decorator to conditionally register a tool based on config."""
        def decorator(func: Callable) -> Callable:
            if is_tool_enabled(name, tool_filter):
                return app.tool(name=name)(func)
            return func  # Return undecorated function (not registered)
        return decorator

    # Generic request tool to cover all API functionality
    @register_tool("probely_request")
    def probely_request(method: str, path: str, params: Optional[Dict[str, Any]] = None,
                        json: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a raw request to Probely API (path relative to base)."""
        return client.raw(method=method, path=path, params=params, json=json, data=data)

    # User Management (read-only)
    @register_tool("probely_get_user")
    def probely_get_user(userId: str) -> Dict[str, Any]:
        return client.get_user(user_id=userId)

    @register_tool("probely_get_api_user")
    def probely_get_api_user(apiUserId: str) -> Dict[str, Any]:
        return client.get_api_user(api_user_id=apiUserId)

    # Account
    @register_tool("probely_get_account")
    def probely_get_account() -> Dict[str, Any]:
        return client.get_account()

    # Roles (read-only)
    @register_tool("probely_get_role")
    def probely_get_role(roleId: str) -> Dict[str, Any]:
        return client.get_role(role_id=roleId)

    # Teams (read-only)
    @register_tool("probely_list_teams")
    def probely_list_teams(page: Optional[int] = None) -> Dict[str, Any]:
        return client.list_teams(page=page)

    @register_tool("probely_get_team")
    def probely_get_team(teamId: str) -> Dict[str, Any]:
        return client.get_team(team_id=teamId)

    # Domains (read-only)
    @register_tool("probely_get_domain")
    def probely_get_domain(domainId: str) -> Dict[str, Any]:
        return client.get_domain(domain_id=domainId)

    # Labels
    @register_tool("probely_list_labels")
    def probely_list_labels(page: Optional[int] = None) -> Dict[str, Any]:
        return client.list_labels(page=page)

    @register_tool("probely_get_label")
    def probely_get_label(labelId: str) -> Dict[str, Any]:
        return client.get_label(label_id=labelId)

    @register_tool("probely_create_label")
    def probely_create_label(name: str, color: Optional[str] = None) -> Dict[str, Any]:
        return client.create_label(name=name, color=color)

    @register_tool("probely_update_label")
    def probely_update_label(labelId: str, name: Optional[str] = None, color: Optional[str] = None) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}
        if name is not None:
            fields["name"] = name
        if color is not None:
            fields["color"] = color
        return client.update_label(label_id=labelId, **fields)

    # Targets
    @register_tool("probely_list_targets")
    def probely_list_targets(page: Optional[int] = None, search: Optional[str] = None) -> Dict[str, Any]:
        return client.list_targets(page=page, search=search)

    @register_tool("probely_get_target")
    def probely_get_target(targetId: str) -> Dict[str, Any]:
        return client.get_target(target_id=targetId)

    @register_tool("probely_create_target")
    def probely_create_target(name: str, url: str, desc: Optional[str] = None, labels: Optional[list[str]] = None) -> Dict[str, Any]:
        """Create a new target. Use labels to assign label names (e.g. ["Agentic", "Production"]).
        Existing labels are reused; missing ones are created automatically."""
        return client.create_target(name=name, url=url, desc=desc, label_names=labels,
                                    default_label=target_defaults.get("default_label"),
                                    name_prefix=target_defaults.get("name_prefix", ""))

    @register_tool("probely_update_target")
    def probely_update_target(targetId: str, name: Optional[str] = None, url: Optional[str] = None,
                              desc: Optional[str] = None, labels: Optional[list[str]] = None) -> Dict[str, Any]:
        """Update a target. Use labels to assign label names (e.g. ["Agentic", "Production"]).
        Existing labels are reused; missing ones are created automatically."""
        fields: Dict[str, Any] = {}
        site_fields: Dict[str, Any] = {}
        if name is not None:
            site_fields["name"] = name
        if url is not None:
            site_fields["url"] = url
        if desc is not None:
            site_fields["desc"] = desc
        if site_fields:
            fields["site"] = site_fields
        if labels is not None:
            fields["labels"] = client.resolve_labels(labels)
        return client.update_target(target_id=targetId, **fields)

    @register_tool("probely_delete_target")
    def probely_delete_target(targetId: str) -> Dict[str, Any]:
        return client.delete_target(target_id=targetId)

    # Login Sequences
    @register_tool("probely_list_sequences")
    def probely_list_sequences(targetId: str, page: Optional[int] = None) -> Dict[str, Any]:
        """List all login sequences for a target."""
        return client.list_sequences(target_id=targetId, page=page)

    @register_tool("probely_get_sequence")
    def probely_get_sequence(targetId: str, sequenceId: str) -> Dict[str, Any]:
        """Get details of a specific login sequence."""
        return client.get_sequence(target_id=targetId, sequence_id=sequenceId)

    @register_tool("probely_create_sequence")
    def probely_create_sequence(targetId: str, name: str, content: str, sequence_type: str = "login", enabled: bool = True,
                                custom_field_mappings: Optional[Any] = None) -> Dict[str, Any]:
        """Create a login sequence. Content must be a JSON string of the sequence steps array. Use custom_field_mappings to configure credentials instead of hardcoding them in the sequence content.

        custom_field_mappings should be a JSON array or JSON array string, e.g.:
        [{"name": "[CUSTOM_USERNAME]", "value": "user@example.com", "value_is_sensitive": false, "enabled": true}]
        """
        mappings = _parse_list_of_dicts(custom_field_mappings)
        return client.create_sequence(target_id=targetId, name=name, sequence_type=sequence_type, content=content, 
                                     enabled=enabled, custom_field_mappings=mappings)

    @register_tool("probely_update_sequence")
    def probely_update_sequence(targetId: str, sequenceId: str, name: Optional[str] = None, 
                                 content: Optional[str] = None, enabled: Optional[bool] = None,
                                 custom_field_mappings: Optional[Any] = None) -> Dict[str, Any]:
        """Update a login sequence. Use custom_field_mappings to configure credentials instead of hardcoding them in the sequence content.
        
        custom_field_mappings should be a JSON array string, e.g.:
        [{"name": "[CUSTOM_USERNAME]", "value": "user@example.com", "value_is_sensitive": false, "enabled": true}]
        """
        fields: Dict[str, Any] = {}
        if name is not None:
            fields["name"] = name
        if content is not None:
            fields["content"] = content
        if enabled is not None:
            fields["enabled"] = enabled
        mappings = _parse_list_of_dicts(custom_field_mappings)
        if mappings is not None:
            fields["custom_field_mappings"] = mappings
        return client.update_sequence(target_id=targetId, sequence_id=sequenceId, **fields)

    @register_tool("probely_delete_sequence")
    def probely_delete_sequence(targetId: str, sequenceId: str) -> Dict[str, Any]:
        """Delete a login sequence."""
        return client.delete_sequence(target_id=targetId, sequence_id=sequenceId)

    # Authentication Configuration
    @register_tool("probely_configure_form_login")
    def probely_configure_form_login(targetId: str, login_url: str, username_field: str, password_field: str,
                                     username: str, password: str, check_pattern: Optional[str] = None) -> Dict[str, Any]:
        """Configure form-based login authentication. Only use this as a fallback when Playwright is NOT available. When Playwright IS available, always record a login sequence instead (probely_create_sequence)."""
        return client.configure_form_login(target_id=targetId, login_url=login_url, username_field=username_field,
                                           password_field=password_field, username=username, password=password,
                                           check_pattern=check_pattern)

    @register_tool("probely_configure_sequence_login")
    def probely_configure_sequence_login(targetId: str, enabled: bool = True) -> Dict[str, Any]:
        """Enable or disable sequence-based login. Call this after creating a login sequence."""
        return client.configure_sequence_login(target_id=targetId, enabled=enabled)

    @register_tool("probely_configure_2fa_totp")
    def probely_configure_2fa_totp(targetId: str, otp_secret: str,
                                   otp_algorithm: str = "SHA1", otp_digits: int = 6) -> Dict[str, Any]:
        """Configure TOTP-based 2FA for a target. Automatically generates a TOTP code from the
        secret and configures it as the OTP placeholder for the login sequence.

        Call this BEFORE creating/updating the login sequence. The response includes an
        ``otp_code`` field — use this exact code hardcoded in the sequence's fill_value step
        for the OTP input. Probely will auto-convert that step to ``fill_otp`` at scan time."""
        totp = _generate_totp(otp_secret, algorithm=otp_algorithm, digits=otp_digits)
        result = client.configure_2fa(target_id=targetId, otp_secret=otp_secret,
                                      otp_placeholder=totp["code"],
                                      otp_algorithm=otp_algorithm, otp_digits=otp_digits,
                                      otp_type="totp")
        result["otp_code"] = totp["code"]
        return result

    @register_tool("probely_disable_2fa")
    def probely_disable_2fa(targetId: str) -> Dict[str, Any]:
        """Disable 2FA/OTP for a target."""
        return client.disable_2fa(target_id=targetId)

    @register_tool("probely_generate_totp")
    def probely_generate_totp(secret: str, algorithm: str = "SHA1", digits: int = 6, period: int = 30) -> Dict[str, Any]:
        """Generate a TOTP code from a secret/seed. Use this when recording login sequences that require 2FA.
        Returns the current TOTP code and its remaining validity in seconds."""
        return _generate_totp(secret, algorithm=algorithm, digits=digits, period=period)

    @register_tool("probely_list_logout_detectors")
    def probely_list_logout_detectors(targetId: str) -> Dict[str, Any]:
        """List all logout detectors for a target."""
        return client.list_logout_detectors(target_id=targetId)

    @register_tool("probely_create_logout_detector")
    def probely_create_logout_detector(targetId: str, detector_type: str, value: str) -> Dict[str, Any]:
        """Create a logout detector for a target.
        
        Args:
            targetId: The target ID
            detector_type: Type of detector - 'text' (text that appears after logout), 
                          'url' (redirect URL after logout), or 'sel' (CSS selector after logout)
            value: The value for the detector (e.g., "Login", "/login", ".login-form")
        """
        return client.create_logout_detector(target_id=targetId, detector_type=detector_type, value=value)

    @register_tool("probely_configure_logout_detection")
    def probely_configure_logout_detection(targetId: str, enabled: bool = True, 
                                           check_session_url: Optional[str] = None,
                                           logout_detector_type: Optional[str] = None,
                                           logout_detector_value: Optional[str] = None,
                                           logout_condition: Optional[str] = None) -> Dict[str, Any]:
        """Configure logout detection for a target. This helps the scanner detect when it needs to re-authenticate.
        
        The Probely API requires BOTH check_session_url AND at least one logout detector to be defined
        before logout detection can be enabled. This function handles the proper ordering automatically.
        
        When no detector is specified, the tool automatically extracts a CSS selector from the target's
        login sequence (typically the username field) and uses it as the logout detector. This is the
        most reliable approach: if the login form elements appear on the page, the user is logged out.
        
        Args:
            targetId: The target ID
            enabled: Whether to enable logout detection (default: True)
            check_session_url: URL to check if session is still valid. Should return 200 when logged in, 
                              and 401/403 when logged out. Common examples: /api/me, /api/user, /api/session
            logout_detector_type: Type of logout detector to create if none exist.
                                  Options: 'sel' (CSS selector - recommended), 'text' (text after logout), 'url' (redirect URL).
                                  If not provided, auto-extracts CSS selector from login sequence, or falls back to 'text: Login'.
            logout_detector_value: Value for the logout detector. Required if logout_detector_type is provided.
            logout_condition: When to consider the target logged out based on detectors.
                              'any' (default) = logged out if ANY detector matches (OR logic).
                              'all' = logged out only if ALL detectors match (AND logic).
                              Use 'all' when some detector patterns also appear on the logged-in page.
        """
        return client.configure_logout_detection(
            target_id=targetId, 
            enabled=enabled, 
            check_session_url=check_session_url,
            logout_detector_type=logout_detector_type,
            logout_detector_value=logout_detector_value,
            logout_condition=logout_condition
        )

    # Extra Hosts
    @register_tool("probely_list_extra_hosts")
    def probely_list_extra_hosts(targetId: str, page: Optional[int] = None) -> Dict[str, Any]:
        return client.list_extra_hosts(target_id=targetId, page=page)

    @register_tool("probely_get_extra_host")
    def probely_get_extra_host(targetId: str, extraHostId: str) -> Dict[str, Any]:
        return client.get_extra_host(target_id=targetId, extra_host_id=extraHostId)

    @register_tool("probely_create_extra_host")
    def probely_create_extra_host(targetId: str, hostname: str, ip_address: str) -> Dict[str, Any]:
        return client.create_extra_host(target_id=targetId, hostname=hostname, ip_address=ip_address)

    @register_tool("probely_update_extra_host")
    def probely_update_extra_host(targetId: str, extraHostId: str, hostname: Optional[str] = None, ip_address: Optional[str] = None) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}
        if hostname is not None:
            fields["hostname"] = hostname
        if ip_address is not None:
            fields["ip_address"] = ip_address
        return client.update_extra_host(target_id=targetId, extra_host_id=extraHostId, **fields)

    @register_tool("probely_delete_extra_host")
    def probely_delete_extra_host(targetId: str, extraHostId: str) -> Dict[str, Any]:
        return client.delete_extra_host(target_id=targetId, extra_host_id=extraHostId)

    # Scans
    @register_tool("probely_list_scans")
    def probely_list_scans(targetId: str, page: Optional[int] = None) -> Dict[str, Any]:
        return client.list_scans(target_id=targetId, page=page)

    @register_tool("probely_get_scan")
    def probely_get_scan(targetId: str, scanId: str) -> Dict[str, Any]:
        return client.get_scan(target_id=targetId, scan_id=scanId)

    @register_tool("probely_start_scan")
    def probely_start_scan(targetId: str, profile: Optional[str] = None) -> Dict[str, Any]:
        return client.start_scan(target_id=targetId, profile=profile)

    @register_tool("probely_stop_scan")
    def probely_stop_scan(targetId: str, scanId: str) -> Dict[str, Any]:
        return client.stop_scan(target_id=targetId, scan_id=scanId)

    @register_tool("probely_cancel_scan")
    def probely_cancel_scan(targetId: str, scanId: str) -> Dict[str, Any]:
        return client.cancel_scan(target_id=targetId, scan_id=scanId)

    # Findings
    @register_tool("probely_list_findings")
    def probely_list_findings(targetId: str, page: Optional[int] = None, severity: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
        return client.list_findings(target_id=targetId, page=page, severity=severity, state=state)

    @register_tool("probely_get_finding")
    def probely_get_finding(targetId: str, findingId: str) -> Dict[str, Any]:
        return client.get_finding(target_id=targetId, finding_id=findingId)

    @register_tool("probely_update_finding")
    def probely_update_finding(targetId: str, findingId: str, state: Optional[str] = None) -> Dict[str, Any]:
        return client.update_finding(target_id=targetId, finding_id=findingId, state=state)

    @register_tool("probely_bulk_update_findings")
    def probely_bulk_update_findings(targetId: str, findingIds: list[str], state: Optional[str] = None) -> Dict[str, Any]:
        return client.bulk_update_findings(target_id=targetId, finding_ids=findingIds, state=state)

    # Settings
    @register_tool("probely_get_target_settings")
    def probely_get_target_settings(targetId: str) -> Dict[str, Any]:
        return client.get_target_settings(target_id=targetId)

    @register_tool("probely_update_target_settings")
    def probely_update_target_settings(targetId: str, excluded_paths: Optional[list[str]] = None,
                                       max_scan_duration: Optional[int] = None, scan_profile: Optional[str] = None) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}
        if excluded_paths is not None:
            fields["excluded_paths"] = excluded_paths
        if max_scan_duration is not None:
            fields["max_scan_duration"] = max_scan_duration
        if scan_profile is not None:
            fields["scan_profile"] = scan_profile
        return client.update_target_settings(target_id=targetId, **fields)

    # Reports (using top-level /report/ endpoint)
    @register_tool("probely_create_scan_report")
    def probely_create_scan_report(scanId: str, report_type: str = "default", format: str = "pdf") -> Dict[str, Any]:
        """Create a report for a scan. Returns report metadata including the report ID.
        
        Args:
            scanId: The scan ID to generate the report for
            report_type: Type of report - "default", "executive", "owasp", "pci", "hipaa", "iso27001"
            format: File format - "pdf" or "html"
        """
        return client.create_scan_report(scan_id=scanId, report_type=report_type, report_format=format)

    @register_tool("probely_download_report")
    def probely_download_report(reportId: str) -> Dict[str, Any]:
        """Download a report by its ID."""
        status, body = client.download_report(report_id=reportId)
        return {"status": status, **body}

    @register_tool("probely_get_report")
    def probely_get_report(reportId: str) -> Dict[str, Any]:
        """Get report metadata/status by ID."""
        return client.get_report(report_id=reportId)

    # Integrations
    @register_tool("probely_list_integrations")
    def probely_list_integrations() -> Dict[str, Any]:
        return client.list_integrations()

    @register_tool("probely_get_integration")
    def probely_get_integration(integrationId: str) -> Dict[str, Any]:
        return client.get_integration(integration_id=integrationId)

    # API Target from Postman
    @register_tool("probely_create_api_target_from_postman")
    def probely_create_api_target_from_postman(name: str, target_url: str, postman_collection_url: Optional[str] = None,
                                               postman_collection_json: Optional[Dict[str, Any]] = None,
                                               desc: Optional[str] = None, labels: Optional[list[str]] = None) -> Dict[str, Any]:
        """Create an API target from a Postman collection. Provide either postman_collection_url or postman_collection_json."""
        import requests
        collection: Dict[str, Any] | None = postman_collection_json
        if collection is None and postman_collection_url:
            r = requests.get(postman_collection_url, timeout=60)
            r.raise_for_status()
            collection = r.json()
        if not collection:
            return {"error": {"message": "Provide postman_collection_url or postman_collection_json"}}
        return client.create_api_target_from_postman(name=name, target_url=target_url, postman_json=collection, desc=desc, label_names=labels,
                                                        default_label=target_defaults.get("default_label"),
                                                        name_prefix=target_defaults.get("name_prefix", ""))

    # API Target from OpenAPI
    @register_tool("probely_create_api_target_from_openapi")
    def probely_create_api_target_from_openapi(name: str, target_url: str, openapi_schema_url: Optional[str] = None,
                                               openapi_schema_json: Optional[Dict[str, Any]] = None,
                                               desc: Optional[str] = None, labels: Optional[list[str]] = None) -> Dict[str, Any]:
        """Create an API target from an OpenAPI/Swagger schema. Provide either openapi_schema_url or openapi_schema_json."""
        import requests
        schema: Dict[str, Any] | None = openapi_schema_json
        if schema is None and openapi_schema_url:
            r = requests.get(openapi_schema_url, timeout=60)
            r.raise_for_status()
            # Handle both JSON and YAML
            content_type = r.headers.get("Content-Type", "")
            if "yaml" in content_type or openapi_schema_url.endswith((".yaml", ".yml")):
                import yaml
                schema = yaml.safe_load(r.text)
            else:
                schema = r.json()
        if not schema:
            return {"error": {"message": "Provide openapi_schema_url or openapi_schema_json"}}
        return client.create_api_target_from_openapi(name=name, target_url=target_url, openapi_schema=schema, desc=desc, label_names=labels,
                                                        default_label=target_defaults.get("default_label"),
                                                        name_prefix=target_defaults.get("name_prefix", ""))

    return app
