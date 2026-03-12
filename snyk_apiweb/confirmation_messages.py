from __future__ import annotations

from typing import Any, List, Optional

from .probely_client import ProbelyClient


def get_target_context(
    client: ProbelyClient, target_id: str
) -> tuple[str, str]:
    """Return (target_name, target_url) for use in confirmation messages."""
    target = client.get_target(target_id=target_id)
    site = target.get("site", {})
    return site.get("name", target_id), site.get("url", target_id)


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------


def create_credential_msg(client: ProbelyClient, name: str, **kw: Any) -> str:
    return f"Create credential '{name}'?"


def update_credential_msg(
    client: ProbelyClient, credentialId: str, **kw: Any
) -> str:
    cred = client.get_credential(credential_id=credentialId)
    cred_name = cred.get("name", credentialId)
    return f"Update credential '{cred_name}'?"


def delete_credential_msg(
    client: ProbelyClient, credentialId: str, **kw: Any
) -> str:
    cred = client.get_credential(credential_id=credentialId)
    cred_name = cred.get("name", credentialId)
    cred_uri = cred.get("uri", credentialId)
    return f"Are you sure you want to delete credential '{cred_name}' (URI: {cred_uri})?"


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


def create_label_msg(client: ProbelyClient, name: str, **kw: Any) -> str:
    return f"Create label '{name}'?"


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------


def create_target_msg(
    client: ProbelyClient, name: str, url: str, **kw: Any
) -> str:
    return f"Create target '{name}' (URL: {url})?"


def update_target_msg(client: ProbelyClient, targetId: str, **kw: Any) -> str:
    target_name, target_url = get_target_context(client, targetId)
    return f"I've prepared the changes for target '{target_name}' (URL: {target_url}). Ready to submit?"


def delete_target_msg(client: ProbelyClient, targetId: str, **kw: Any) -> str:
    target_name, target_url = get_target_context(client, targetId)
    return f"Are you sure you want to delete target '{target_name}' (URL: {target_url})?"


def create_api_target_from_postman_msg(
    client: ProbelyClient, name: str, target_url: str, **kw: Any
) -> str:
    return f"Create API target '{name}' (URL: {target_url}) from Postman collection?"


def create_api_target_from_openapi_msg(
    client: ProbelyClient, name: str, target_url: str, **kw: Any
) -> str:
    return (
        f"Create API target '{name}' (URL: {target_url}) from OpenAPI schema?"
    )


# ---------------------------------------------------------------------------
# Sequences
# ---------------------------------------------------------------------------


def create_sequence_msg(
    client: ProbelyClient, targetId: str, name: str, **kw: Any
) -> str:
    target_name, target_url = get_target_context(client, targetId)
    return f"Create login sequence '{name}' for target '{target_name}' (URL: {target_url})?"


def update_sequence_msg(
    client: ProbelyClient, targetId: str, sequenceId: str, **kw: Any
) -> str:
    seq = client.get_sequence(target_id=targetId, sequence_id=sequenceId)
    seq_name = seq.get("name", sequenceId)
    target_name, target_url = get_target_context(client, targetId)
    return f"Update login sequence '{seq_name}' for target '{target_name}' (URL: {target_url})?"


def delete_sequence_msg(
    client: ProbelyClient, targetId: str, sequenceId: str, **kw: Any
) -> str:
    seq = client.get_sequence(target_id=targetId, sequence_id=sequenceId)
    seq_name = seq.get("name", sequenceId)
    target_name, target_url = get_target_context(client, targetId)
    return f"Are you sure you want to delete login sequence '{seq_name}' for target '{target_name}' (URL: {target_url})?"


# ---------------------------------------------------------------------------
# Authentication configuration
# ---------------------------------------------------------------------------


def configure_form_login_msg(
    client: ProbelyClient, targetId: str, login_url: str, **kw: Any
) -> str:
    target_name, target_url = get_target_context(client, targetId)
    return f"Configure form login (login URL: {login_url}) for target '{target_name}' (URL: {target_url})?"


def configure_sequence_login_msg(
    client: ProbelyClient, targetId: str, enabled: bool = True, **kw: Any
) -> str:
    target_name, target_url = get_target_context(client, targetId)
    action = "Enable" if enabled else "Disable"
    return f"{action} sequence login for target '{target_name}' (URL: {target_url})?"


def configure_2fa_totp_msg(
    client: ProbelyClient, targetId: str, **kw: Any
) -> str:
    target_name, target_url = get_target_context(client, targetId)
    return (
        f"Configure TOTP 2FA for target '{target_name}' (URL: {target_url})?"
    )


def disable_2fa_msg(client: ProbelyClient, targetId: str, **kw: Any) -> str:
    target_name, target_url = get_target_context(client, targetId)
    return f"Disable 2FA for target '{target_name}' (URL: {target_url})?"


# ---------------------------------------------------------------------------
# Logout detection
# ---------------------------------------------------------------------------


def create_logout_detector_msg(
    client: ProbelyClient,
    targetId: str,
    detector_type: str,
    value: str,
    **kw: Any,
) -> str:
    target_name, target_url = get_target_context(client, targetId)
    return f"Create logout detector (type: {detector_type}, value: '{value}') for target '{target_name}' (URL: {target_url})?"


def configure_logout_detection_msg(
    client: ProbelyClient, targetId: str, enabled: bool = True, **kw: Any
) -> str:
    target_name, target_url = get_target_context(client, targetId)
    action = "Enable" if enabled else "Disable"
    return f"{action} logout detection for target '{target_name}' (URL: {target_url})?"


# ---------------------------------------------------------------------------
# Extra hosts
# ---------------------------------------------------------------------------


def create_extra_host_msg(
    client: ProbelyClient, targetId: str, hostname: str, **kw: Any
) -> str:
    target_name, target_url = get_target_context(client, targetId)
    return f"Create extra host '{hostname}' for target '{target_name}' (URL: {target_url})?"


def update_extra_host_msg(
    client: ProbelyClient, targetId: str, extraHostId: str, **kw: Any
) -> str:
    host = client.get_extra_host(target_id=targetId, extra_host_id=extraHostId)
    hostname = host.get("hostname", extraHostId)
    target_name, target_url = get_target_context(client, targetId)
    return f"Update extra host '{hostname}' for target '{target_name}' (URL: {target_url})?"


def delete_extra_host_msg(
    client: ProbelyClient, targetId: str, extraHostId: str, **kw: Any
) -> str:
    host = client.get_extra_host(target_id=targetId, extra_host_id=extraHostId)
    hostname = host.get("hostname", extraHostId)
    target_name, target_url = get_target_context(client, targetId)
    return f"Are you sure you want to delete extra host '{hostname}' for target '{target_name}' (URL: {target_url})?"


# ---------------------------------------------------------------------------
# Scans
# ---------------------------------------------------------------------------


def start_scan_msg(client: ProbelyClient, targetId: str, **kw: Any) -> str:
    target_name, target_url = get_target_context(client, targetId)
    return f"Start scan for target '{target_name}' (URL: {target_url})?"


def stop_scan_msg(
    client: ProbelyClient, targetId: str, scanId: str, **kw: Any
) -> str:
    target_name, target_url = get_target_context(client, targetId)
    return f"Are you sure you want to stop scan {scanId} for target '{target_name}' (URL: {target_url})?"


def cancel_scan_msg(
    client: ProbelyClient, targetId: str, scanId: str, **kw: Any
) -> str:
    target_name, target_url = get_target_context(client, targetId)
    return f"Are you sure you want to cancel scan {scanId} for target '{target_name}' (URL: {target_url})?"


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


def update_finding_msg(
    client: ProbelyClient,
    targetId: str,
    findingId: str,
    state: Optional[str] = None,
    **kw: Any,
) -> str:
    target_name, target_url = get_target_context(client, targetId)
    state_str = state or "changed"
    return f"Update finding {findingId} to state '{state_str}' for target '{target_name}' (URL: {target_url})?"


def bulk_update_findings_msg(
    client: ProbelyClient,
    targetId: str,
    findingIds: List[str],
    state: Optional[str] = None,
    **kw: Any,
) -> str:
    state_str = state or "changed"
    target_name, target_url = get_target_context(client, targetId)
    return f"Are you sure you want to bulk update {len(findingIds)} finding(s) for target '{target_name}' (URL: {target_url}) to state '{state_str}'?"


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def update_target_settings_msg(
    client: ProbelyClient, targetId: str, **kw: Any
) -> str:
    target_name, target_url = get_target_context(client, targetId)
    return f"Update settings for target '{target_name}' (URL: {target_url})?"


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def create_scanreport_msg(
    client: ProbelyClient,
    scanId: str,
    report_type: str = "default",
    format: str = "pdf",
    **kw: Any,
) -> str:
    return f"Create {report_type} report ({format}) for scan {scanId}?"
