from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class ProbelyClient:
    def __init__(self, base_url: str, api_key: str, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"JWT {self.api_key}",
            "Accept": "application/json",
        })

    def _url(self, path: str) -> str:
        path = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{path}"

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8),
           retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)))
    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        url = self._url(path)
        req_headers = dict(self._session.headers)
        if headers:
            req_headers.update(headers)
        resp = self._session.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json,
            data=data,
            files=files,
            headers=req_headers,
            timeout=self.timeout,
        )
        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            json_data = resp.json()
            # Handle both dict and list responses (some endpoints return arrays)
            if isinstance(json_data, dict):
                body: Dict[str, Any] = json_data
            else:
                body = {"results": json_data}
        else:
            body = {"raw": resp.text}
        if not resp.ok:
            # include more details for troubleshooting
            if isinstance(body, dict):
                body.setdefault("error", {})
                body["error"].update({
                    "status": resp.status_code,
                    "reason": resp.reason,
                    "url": url,
                })
        return resp.status_code, body

    # Convenience wrappers for common resources
    # Users
    def list_users(self, page: Optional[int] = None) -> Dict[str, Any]:
        return self.request("GET", "/users/", params={"page": page} if page else None)[1]

    def get_user(self, user_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/users/{user_id}/")[1]

    def create_user(self, email: str, name: str, role: Optional[str] = None) -> Dict[str, Any]:
        payload = {"email": email, "name": name}
        if role:
            payload["role"] = role
        return self.request("POST", "/users/", json=payload)[1]

    def update_user(self, user_id: str, **fields: Any) -> Dict[str, Any]:
        return self.request("PATCH", f"/users/{user_id}/", json=fields)[1]

    def delete_user(self, user_id: str) -> Dict[str, Any]:
        return self.request("DELETE", f"/users/{user_id}/")[1]

    # API Users
    def list_api_users(self, page: Optional[int] = None) -> Dict[str, Any]:
        return self.request("GET", "/api-users/", params={"page": page} if page else None)[1]

    def get_api_user(self, api_user_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/api-users/{api_user_id}/")[1]

    def create_api_user(self, name: str, permissions: Optional[list[str]] = None) -> Dict[str, Any]:
        payload = {"name": name}
        if permissions is not None:
            payload["permissions"] = permissions
        return self.request("POST", "/api-users/", json=payload)[1]

    def delete_api_user(self, api_user_id: str) -> Dict[str, Any]:
        return self.request("DELETE", f"/api-users/{api_user_id}/")[1]

    # Account
    def get_account(self) -> Dict[str, Any]:
        return self.request("GET", "/account/")[1]

    def update_account(self, **fields: Any) -> Dict[str, Any]:
        return self.request("PATCH", "/account/", json=fields)[1]

    # Roles & Permissions
    def list_roles(self, page: Optional[int] = None) -> Dict[str, Any]:
        return self.request("GET", "/roles/", params={"page": page} if page else None)[1]

    def get_role(self, role_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/roles/{role_id}/")[1]

    def list_permissions(self, page: Optional[int] = None) -> Dict[str, Any]:
        return self.request("GET", "/permissions/", params={"page": page} if page else None)[1]

    # Teams
    def list_teams(self, page: Optional[int] = None) -> Dict[str, Any]:
        return self.request("GET", "/teams/", params={"page": page} if page else None)[1]

    def get_team(self, team_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/teams/{team_id}/")[1]

    def create_team(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        payload = {"name": name}
        if description:
            payload["description"] = description
        return self.request("POST", "/teams/", json=payload)[1]

    def update_team(self, team_id: str, **fields: Any) -> Dict[str, Any]:
        return self.request("PATCH", f"/teams/{team_id}/", json=fields)[1]

    def delete_team(self, team_id: str) -> Dict[str, Any]:
        return self.request("DELETE", f"/teams/{team_id}/")[1]

    # Domains
    def list_domains(self, page: Optional[int] = None) -> Dict[str, Any]:
        return self.request("GET", "/domains/", params={"page": page} if page else None)[1]

    def get_domain(self, domain_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/domains/{domain_id}/")[1]

    def create_domain(self, name: str) -> Dict[str, Any]:
        return self.request("POST", "/domains/", json={"name": name})[1]

    def verify_domain(self, domain_id: str) -> Dict[str, Any]:
        return self.request("POST", f"/domains/{domain_id}/verify/")[1]

    def delete_domain(self, domain_id: str) -> Dict[str, Any]:
        return self.request("DELETE", f"/domains/{domain_id}/")[1]

    # Labels
    def list_labels(self, page: Optional[int] = None) -> Dict[str, Any]:
        return self.request("GET", "/labels/", params={"page": page} if page else None)[1]

    def get_label(self, label_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/labels/{label_id}/")[1]

    def create_label(self, name: str, color: Optional[str] = None) -> Dict[str, Any]:
        payload = {"name": name}
        if color:
            payload["color"] = color
        return self.request("POST", "/labels/", json=payload)[1]

    def update_label(self, label_id: str, **fields: Any) -> Dict[str, Any]:
        return self.request("PATCH", f"/labels/{label_id}/", json=fields)[1]

    def delete_label(self, label_id: str) -> Dict[str, Any]:
        return self.request("DELETE", f"/labels/{label_id}/")[1]

    # Targets
    def list_targets(self, page: Optional[int] = None, search: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if page:
            params["page"] = page
        if search:
            params["search"] = search
        return self.request("GET", "/targets/", params=params or None)[1]

    def get_target(self, target_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/targets/{target_id}/")[1]

    def create_target(self, name: str, url: str, desc: Optional[str] = None, label_ids: Optional[list[str]] = None) -> Dict[str, Any]:
        """Create a new target. Both name and URL must be nested under 'site' per the Probely API."""
        payload: Dict[str, Any] = {
            "site": {
                "name": name,
                "url": url
            }
        }
        if desc:
            payload["site"]["desc"] = desc
        if label_ids:
            # Labels must be provided as list of label objects with 'id' field
            payload["labels"] = [{"id": lid} for lid in label_ids]
        return self.request("POST", "/targets/", json=payload)[1]

    def update_target(self, target_id: str, **fields: Any) -> Dict[str, Any]:
        return self.request("PATCH", f"/targets/{target_id}/", json=fields)[1]

    def delete_target(self, target_id: str) -> Dict[str, Any]:
        return self.request("DELETE", f"/targets/{target_id}/")[1]

    def verify_target(self, target_id: str) -> Dict[str, Any]:
        return self.request("POST", f"/targets/{target_id}/verify/")[1]

    # Login Sequences
    def list_sequences(self, target_id: str, page: Optional[int] = None) -> Dict[str, Any]:
        return self.request("GET", f"/targets/{target_id}/sequences/", params={"page": page} if page else None)[1]

    def get_sequence(self, target_id: str, sequence_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/targets/{target_id}/sequences/{sequence_id}/")[1]

    def create_sequence(self, target_id: str, name: str, sequence_type: str, content: str, enabled: bool = True,
                       custom_field_mappings: Optional[list[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Create a login sequence. Content must be a JSON string of the sequence steps."""
        payload: Dict[str, Any] = {
            "name": name,
            "type": sequence_type,
            "content": content,
            "enabled": enabled
        }
        if custom_field_mappings is not None:
            payload["custom_field_mappings"] = custom_field_mappings
        return self.request("POST", f"/targets/{target_id}/sequences/", json=payload)[1]

    def update_sequence(self, target_id: str, sequence_id: str, **fields: Any) -> Dict[str, Any]:
        return self.request("PATCH", f"/targets/{target_id}/sequences/{sequence_id}/", json=fields)[1]

    def delete_sequence(self, target_id: str, sequence_id: str) -> Dict[str, Any]:
        return self.request("DELETE", f"/targets/{target_id}/sequences/{sequence_id}/")[1]

    # Authentication Configuration (via target site settings)
    def configure_form_login(self, target_id: str, login_url: str, username_field: str, password_field: str,
                             username: str, password: str, check_pattern: Optional[str] = None) -> Dict[str, Any]:
        """Configure form-based login authentication for a target."""
        payload: Dict[str, Any] = {
            "site": {
                "has_form_login": True,
                "form_login_url": login_url,
                "form_login": [
                    {"name": username_field, "value": username},
                    {"name": password_field, "value": password}
                ],
                "auth_enabled": True
            }
        }
        if check_pattern:
            payload["site"]["form_login_check_pattern"] = check_pattern
        return self.request("PATCH", f"/targets/{target_id}/", json=payload)[1]

    def configure_sequence_login(self, target_id: str, enabled: bool = True) -> Dict[str, Any]:
        """Enable or disable sequence-based login authentication for a target."""
        payload: Dict[str, Any] = {
            "site": {
                "has_sequence_login": enabled,
                "auth_enabled": enabled
            }
        }
        return self.request("PATCH", f"/targets/{target_id}/", json=payload)[1]

    def configure_2fa(self, target_id: str, otp_secret: str, otp_placeholder: str = "{{OTP}}",
                      otp_algorithm: str = "SHA1", otp_digits: int = 6, otp_type: str = "totp") -> Dict[str, Any]:
        """Configure 2FA/OTP settings for a target."""
        payload: Dict[str, Any] = {
            "site": {
                "has_otp": True,
                "otp_secret": otp_secret,
                "otp_login_sequence_totp_value": otp_placeholder,
                "otp_algorithm": otp_algorithm,
                "otp_digits": otp_digits,
                "otp_type": otp_type
            }
        }
        return self.request("PATCH", f"/targets/{target_id}/", json=payload)[1]

    def disable_2fa(self, target_id: str) -> Dict[str, Any]:
        """Disable 2FA/OTP for a target."""
        payload: Dict[str, Any] = {
            "site": {
                "has_otp": False,
                "otp_secret": ""
            }
        }
        return self.request("PATCH", f"/targets/{target_id}/", json=payload)[1]

    def list_logout_detectors(self, target_id: str) -> Dict[str, Any]:
        """List logout detectors for a target."""
        return self.request("GET", f"/targets/{target_id}/logout/")[1]

    def create_logout_detector(self, target_id: str, detector_type: str, value: str) -> Dict[str, Any]:
        """Create a logout detector for a target.
        
        Args:
            target_id: The target ID
            detector_type: Type of detector - 'text', 'url', or 'sel' (CSS selector)
            value: The value for the detector (e.g., "Login", "/login", ".login-form")
        """
        return self.request("POST", f"/targets/{target_id}/logout/", 
                          json={"type": detector_type, "value": value})[1]

    def configure_logout_detection(self, target_id: str, enabled: bool = True, 
                                   check_session_url: Optional[str] = None,
                                   logout_detector_type: Optional[str] = None,
                                   logout_detector_value: Optional[str] = None) -> Dict[str, Any]:
        """Configure logout detection for a target.
        
        Args:
            target_id: The target ID
            enabled: Whether to enable logout detection
            check_session_url: URL to check if session is still valid (should return 401/403 when logged out)
            logout_detector_type: Type of logout detector - 'text', 'url', or 'sel'. 
                                  Required when enabling logout detection if no detectors exist.
            logout_detector_value: Value for the logout detector. 
                                   Required when enabling logout detection if no detectors exist.
        
        Note: The Probely API requires BOTH check_session_url AND at least one logout detector 
        to be defined before logout_detection can be enabled. This function handles the proper
        ordering automatically.
        """
        if enabled:
            # Step 1: Set check_session_url if provided
            if check_session_url is not None:
                url_payload: Dict[str, Any] = {
                    "site": {
                        "check_session_url": check_session_url
                    }
                }
                self.request("PATCH", f"/targets/{target_id}/", json=url_payload)
            
            # Step 2: Check if logout detectors exist, create one if needed
            try:
                detectors = self.list_logout_detectors(target_id)
                detector_list = detectors.get("results", [])
            except:
                detector_list = []
            
            if not detector_list:
                # No logout detectors exist, we need to create one
                if logout_detector_type and logout_detector_value:
                    self.create_logout_detector(target_id, logout_detector_type, logout_detector_value)
                else:
                    # Try to find a CSS selector from the login sequence to use as logout detector
                    # This is the most reliable approach: if the login form elements appear, user is logged out
                    css_selector = self._find_login_sequence_selector(target_id)
                    if css_selector:
                        self.create_logout_detector(target_id, "sel", css_selector)
                    else:
                        # Fallback to text-based detector if no login sequence found
                        self.create_logout_detector(target_id, "text", "Login")
            
            # Step 3: Enable logout detection
            enable_payload: Dict[str, Any] = {
                "site": {
                    "logout_detection_enabled": True
                }
            }
            return self.request("PATCH", f"/targets/{target_id}/", json=enable_payload)[1]
        else:
            # Disabling logout detection or setting URL without enabling
            payload: Dict[str, Any] = {
                "site": {
                    "logout_detection_enabled": enabled
                }
            }
            if check_session_url is not None:
                payload["site"]["check_session_url"] = check_session_url
            return self.request("PATCH", f"/targets/{target_id}/", json=payload)[1]

    def _find_login_sequence_selector(self, target_id: str) -> Optional[str]:
        """Find a CSS selector from the target's login sequence to use as logout detector.
        
        Returns the first CSS selector found in the login sequence (typically username field),
        or None if no login sequence exists.
        """
        import json
        try:
            sequences = self.list_sequences(target_id)
            for seq in sequences.get("results", []):
                if seq.get("type") == "login" and seq.get("enabled"):
                    content = seq.get("content", "")
                    if isinstance(content, str):
                        steps = json.loads(content)
                    else:
                        steps = content
                    
                    # Find the first fill_value step with a CSS selector (usually username field)
                    for step in steps:
                        if step.get("type") == "fill_value" and step.get("css"):
                            return step["css"]
        except Exception:
            pass
        return None

    # Extra Hosts
    def list_extra_hosts(self, target_id: str, page: Optional[int] = None) -> Dict[str, Any]:
        return self.request("GET", f"/targets/{target_id}/extra-hosts/", params={"page": page} if page else None)[1]

    def get_extra_host(self, target_id: str, extra_host_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/targets/{target_id}/extra-hosts/{extra_host_id}/")[1]

    def create_extra_host(self, target_id: str, hostname: str, ip_address: str) -> Dict[str, Any]:
        return self.request("POST", f"/targets/{target_id}/extra-hosts/", json={"hostname": hostname, "ip_address": ip_address})[1]

    def update_extra_host(self, target_id: str, extra_host_id: str, **fields: Any) -> Dict[str, Any]:
        return self.request("PATCH", f"/targets/{target_id}/extra-hosts/{extra_host_id}/", json=fields)[1]

    def delete_extra_host(self, target_id: str, extra_host_id: str) -> Dict[str, Any]:
        return self.request("DELETE", f"/targets/{target_id}/extra-hosts/{extra_host_id}/")[1]

    # Scans
    def list_scans(self, target_id: str, page: Optional[int] = None) -> Dict[str, Any]:
        return self.request("GET", f"/targets/{target_id}/scans/", params={"page": page} if page else None)[1]

    def get_scan(self, target_id: str, scan_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/targets/{target_id}/scans/{scan_id}/")[1]

    def start_scan(self, target_id: str, profile: Optional[str] = None) -> Dict[str, Any]:
        payload = {"profile": profile} if profile else None
        return self.request("POST", f"/targets/{target_id}/scans/", json=payload)[1]

    def stop_scan(self, target_id: str, scan_id: str) -> Dict[str, Any]:
        return self.request("POST", f"/targets/{target_id}/scans/{scan_id}/stop/")[1]

    def cancel_scan(self, target_id: str, scan_id: str) -> Dict[str, Any]:
        return self.request("POST", f"/targets/{target_id}/scans/{scan_id}/cancel/")[1]

    # Findings
    def list_findings(self, target_id: str, page: Optional[int] = None, severity: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if page:
            params["page"] = page
        if severity:
            params["severity"] = severity
        if state:
            params["state"] = state
        return self.request("GET", f"/targets/{target_id}/findings/", params=params or None)[1]

    def get_finding(self, target_id: str, finding_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/targets/{target_id}/findings/{finding_id}/")[1]

    def update_finding(self, target_id: str, finding_id: str, state: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if state:
            payload["state"] = state
        return self.request("PATCH", f"/targets/{target_id}/findings/{finding_id}/", json=payload or None)[1]

    def bulk_update_findings(self, target_id: str, finding_ids: list[str], state: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"findingIds": finding_ids}
        if state:
            payload["state"] = state
        return self.request("POST", f"/targets/{target_id}/findings/bulk-update/", json=payload)[1]

    # Target Settings
    def get_target_settings(self, target_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/targets/{target_id}/settings/")[1]

    def update_target_settings(self, target_id: str, **fields: Any) -> Dict[str, Any]:
        return self.request("PATCH", f"/targets/{target_id}/settings/", json=fields)[1]

    # Reports (using top-level /report/ endpoint)
    def create_scan_report(self, scan_id: str, report_type: str = "default",
                           report_format: str = "pdf") -> Dict[str, Any]:
        """Create a report for a scan. Returns report metadata including the report ID.
        
        Args:
            scan_id: The scan ID to generate the report for
            report_type: Type of report. Options include:
                - "default" - Standard vulnerability report
                - "executive" - Executive summary
                - "owasp" - OWASP Top 10
                - "pci" - PCI-DSS compliance
                - "hipaa" - HIPAA compliance
                - "iso27001" - ISO 27001 compliance
            report_format: File format - "pdf" or "html"
        """
        payload: Dict[str, Any] = {
            "scan": scan_id,
            "type": report_type,
            "format": report_format
        }
        return self.request("POST", "/report/", json=payload)[1]

    def download_report(self, report_id: str) -> Tuple[int, Dict[str, Any]]:
        """Download a report by its ID. Returns the report content."""
        return self.request("GET", f"/report/{report_id}/download/")

    def get_report(self, report_id: str) -> Dict[str, Any]:
        """Get report metadata/status by ID."""
        return self.request("GET", f"/report/{report_id}/")[1]

    # Integrations (generic placeholders; exact endpoints may vary)
    def list_integrations(self) -> Dict[str, Any]:
        return self.request("GET", "/integrations/")[1]

    def get_integration(self, integration_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/integrations/{integration_id}/")[1]

    # API Target via Postman Collection (best-effort; endpoint may vary by Probely account)
    def create_api_target_from_postman(self, name: str, target_url: str, postman_json: Dict[str, Any], desc: Optional[str] = None, labels: Optional[list[str]] = None) -> Dict[str, Any]:
        # Step 1: Create target
        target = self.create_target(name=name, url=target_url, desc=desc, labels=labels)
        target_id = target.get("id") or target.get("target_id") or target.get("uuid")
        if not target_id:
            return {"error": {"message": "Could not determine created target id", "target_response": target}}
        # Step 2: Attempt to attach Postman collection to target (endpoint may differ)
        # Try a few common patterns
        candidates = [
            f"/targets/{target_id}/apis/import/postman/",
            f"/targets/{target_id}/apis/import/",
            f"/targets/{target_id}/api/import/",
        ]
        last_resp: Dict[str, Any] | None = None
        for path in candidates:
            status, body = self.request(
                method="POST",
                path=path,
                json={"collection": postman_json},
                headers={"Content-Type": "application/json"},
            )
            last_resp = body
            if 200 <= status < 300:
                return {
                    "target_id": target_id,
                    "import": body,
                }
        return {
            "target_id": target_id,
            "import_error": last_resp or {"message": "No import endpoint succeeded"},
        }

    # API Target via OpenAPI Schema (best-effort; endpoint may vary by Probely account)
    def create_api_target_from_openapi(self, name: str, target_url: str, openapi_schema: Dict[str, Any], desc: Optional[str] = None, labels: Optional[list[str]] = None) -> Dict[str, Any]:
        # Step 1: Create target
        target = self.create_target(name=name, url=target_url, desc=desc, labels=labels)
        target_id = target.get("id") or target.get("target_id") or target.get("uuid")
        if not target_id:
            return {"error": {"message": "Could not determine created target id", "target_response": target}}
        # Step 2: Attempt to attach OpenAPI schema to target (endpoint may differ)
        # Try a few common patterns
        candidates = [
            f"/targets/{target_id}/apis/import/openapi/",
            f"/targets/{target_id}/apis/import/swagger/",
            f"/targets/{target_id}/apis/import/",
            f"/targets/{target_id}/api/import/openapi/",
        ]
        last_resp: Dict[str, Any] | None = None
        for path in candidates:
            status, body = self.request(
                method="POST",
                path=path,
                json={"schema": openapi_schema},
                headers={"Content-Type": "application/json"},
            )
            last_resp = body
            if 200 <= status < 300:
                return {
                    "target_id": target_id,
                    "import": body,
                }
        return {
            "target_id": target_id,
            "import_error": last_resp or {"message": "No import endpoint succeeded"},
        }

    # Generic fallback
    def raw(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None,
            data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.request(method, path, params=params, json=json, data=data)[1]
