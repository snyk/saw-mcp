from __future__ import annotations

import base64
import functools
import hashlib
import hmac
import json
import logging
import re
import struct
import time
from textwrap import dedent
from typing import Any, Callable, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import Field

from .config import (
    get_probely_api_key,
    get_probely_base_url,
    get_target_defaults,
    get_tool_filter,
    is_tool_enabled,
    load_config,
)
from .probely_client import ProbelyClient, current_tool_name

logger = logging.getLogger(__name__)


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
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
            # Single object → wrap in a list
            if isinstance(parsed, dict):
                return [parsed]
        except (json.JSONDecodeError, TypeError):
            pass
        # Fallback: MCP frameworks may deliver Python-repr strings (single
        # quotes, True/False instead of true/false).  Try ast.literal_eval.
        import ast

        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
        except (ValueError, SyntaxError):
            pass
    # Single dict passed as a native object → wrap in a list
    if isinstance(value, dict):
        return [value]
    raise ValueError(
        f"Expected a JSON array (list of objects), got: {type(value).__name__}. Value: {repr(value)[:200]}"
    )


def _generate_totp(
    secret: str, algorithm: str = "SHA1", digits: int = 6, period: int = 30
) -> Dict[str, Any]:
    """Generate a TOTP code from a base32 secret.

    Returns dict with ``code``, ``remaining_seconds``, ``algorithm``, and ``digits``.
    """
    clean = re.sub(r"[\s-]", "", secret).upper()
    padding = (8 - len(clean) % 8) % 8
    key = base64.b32decode(clean + "=" * padding)

    hash_func = getattr(hashlib, algorithm.lower(), hashlib.sha1)
    now = int(time.time())
    counter = now // period
    remaining = period - (now % period)

    msg = struct.pack(">Q", counter)
    mac = hmac.new(key, msg, hash_func).digest()
    offset = mac[-1] & 0x0F
    code_int = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    code = str(code_int % (10**digits)).zfill(digits)

    return {
        "code": code,
        "remaining_seconds": remaining,
        "algorithm": algorithm,
        "digits": digits,
    }


def build_server() -> FastMCP:
    cfg = load_config()
    base_url = get_probely_base_url(cfg)
    api_key = get_probely_api_key(cfg)
    client = ProbelyClient(base_url=base_url, api_key=api_key)
    tool_filter = get_tool_filter(cfg)
    target_defaults = get_target_defaults(cfg)

    server_name = cfg.get("server", {}).get("name", "Snyk API & Web")
    logger.info("Building MCP server '%s' (%s)", server_name, base_url)
    app = FastMCP(server_name)

    def register_tool(name: str) -> Callable:
        """Decorator to conditionally register a tool based on config."""

        def decorator(func: Callable) -> Callable:
            if is_tool_enabled(name, tool_filter):
                # Wrap the function to set the tool name context before calling
                @functools.wraps(func)
                def wrapper(*args: Any, **kwargs: Any) -> Any:
                    token = current_tool_name.set(name)
                    try:
                        return func(*args, **kwargs)
                    finally:
                        current_tool_name.reset(token)

                return app.tool(name=name)(wrapper)
            return func  # Return undecorated function (not registered)

        return decorator

    @app.prompt(
        name="saw_web_target_configuration",
        description=(
            "Help configure a Snyk API & Web web target with authentication, "
            "login sequence setup, logout detection, extra hosts, and "
            "optional TOTP."
        ),
        tags={"saw", "prompts", "web-target"},
    )
    def saw_web_target_configuration(
        url: str = Field(
            description=(
                "Base URL of the web application, for example "
                "`https://app.example.com`."
            )
        ),
        username: str = Field(
            description="Username or email used to authenticate."
        ),
        password: str = Field(description="Password used to authenticate."),
        name: str = Field(
            default="auto",
            description=(
                "Target name to use. If `auto`, derive it from the user "
                "input, then the page title, then the FQDN."
            ),
        ),
        labels: str = Field(
            default="default",
            description=(
                "JSON string array of labels, or `default` to omit the "
                "`labels` parameter."
            ),
        ),
        totp_seed: str = Field(
            default="none",
            description="TOTP seed for 2FA, or `none` if 2FA is not required.",
        ),
    ) -> str:
        """Help configure a web target."""
        return (
            dedent(
                """
            Configure a Snyk API & Web web target for an authenticated web
            application.

            Target details:
            - URL: `{url}`
            - Name: `{name}`
            - Labels: `{labels}`
            - Username: `{username}`
            - Password: `{password}`
            - 2FA TOTP seed: `{totp_seed}`

            Requirements:
            - First, read the skill file at `/<basedir>/saw-mcp/config/skills/saw-web-target-configuration/SKILL.md` and follow it exactly.
            - Use a login sequence when Playwright is available. Do not use form login unless Playwright is unavailable.
            - Derive the target name in this order if needed: user-provided name, then site `<title>`, then FQDN.
            - If labels are `default`, do not pass a `labels` parameter.
            - Create a new target; do not search for or reuse an existing one.
            - Detect and configure any required extra hosts.
            - Configure logout detection explicitly with `check_session_url`, `logout_detector_type`, and `logout_detector_value`.
            - If 2FA is enabled, configure TOTP before creating the login sequence.
            - Use credentials management by default: store the password via probely_create_credential and link it in `custom_field_mappings`. If the user explicitly declines, inline values are allowed. When multiple targets share the same credential and it already exists and is_sensitive=True, prompt the user to deobfuscate it in order to allow reuse.

            Return:
            - Target ID
            - Final target name
            - URL
            - Login sequence status
            - Logout detection status
            - Extra hosts added
            - Snyk API & Web link in this format: `https://plus.probely.app/targets/{{targetId}}`

            At the end, summarize the configured target in a table.
            """
            )
            .strip()
            .format(
                url=url,
                name=name,
                labels=labels,
                username=username,
                password=password,
                totp_seed=totp_seed,
            )
        )

    @app.prompt(
        name="saw_api_target_configuration",
        description=(
            "Help configure a Snyk API & Web API target from an OpenAPI "
            "schema, Swagger document, Postman collection, or generated "
            "schema."
        ),
        tags={"saw", "prompts", "api-target"},
    )
    def saw_api_target_configuration(
        base_url: str = Field(
            description=(
                "Base URL of the API target, for example "
                "`https://api.example.com`."
            )
        ),
        source_type: str = Field(
            description="One of `openapi`, `postman`, or `generate`."
        ),
        name: str = Field(
            default="auto",
            description=(
                "Target name to use. If `auto`, derive it from user input, "
                "then schema title or collection name, then the domain."
            ),
        ),
        labels: str = Field(
            default="default",
            description=(
                "JSON string array of labels, or `default` to omit the "
                "`labels` parameter."
            ),
        ),
        openapi_schema_url: str = Field(
            default="none",
            description="URL of the OpenAPI or Swagger schema, or `none`.",
        ),
        openapi_schema_content: str = Field(
            default="none",
            description="File path or inline JSON/YAML schema content, or `none`.",
        ),
        postman_collection_url: str = Field(
            default="none",
            description="URL of the Postman collection, or `none`.",
        ),
        postman_collection_content: str = Field(
            default="none",
            description="File path or inline JSON collection content, or `none`.",
        ),
        authentication: str = Field(
            default="none",
            description=(
                "One of `none`, `apiKey`, `bearer`, `oauth`, or `basic`."
            ),
        ),
        authentication_details: str = Field(
            default="none",
            description="Authentication headers, token, credentials, or `none`.",
        ),
    ) -> str:
        """Help configure an API target."""
        return (
            dedent(
                """
            Configure a Snyk API & Web API target for an API described by an
            OpenAPI/Swagger schema or a Postman collection.

            Target details:
            - Base URL: `{base_url}`
            - Name: `{name}`
            - Labels: `{labels}`
            - Schema source type: `{source_type}`
            - OpenAPI schema URL: `{openapi_schema_url}`
            - OpenAPI schema file/content: `{openapi_schema_content}`
            - Postman collection URL: `{postman_collection_url}`
            - Postman collection file/content: `{postman_collection_content}`
            - Authentication: `{authentication}`
            - Authentication details: `{authentication_details}`

            Requirements:
            - First, read the skill file at `/<basedir>/saw-mcp/config/skills/saw-api-target-configuration/SKILL.md` and follow it exactly.
            - Derive the target name in this order if needed: user-provided name, then schema title or Postman collection name, then the domain from the base URL.
            - If labels are `default`, do not pass a `labels` parameter.
            - Create a new target; do not search for or reuse an existing one.
            - If the source type is `openapi`, validate the schema before uploading it and fix any violations first.
            - When the user provides an OpenAPI schema URL, do not fetch the schema JSON from that URL; pass it as `openapi_schema_url` only.
            - If neither an OpenAPI schema nor a Postman collection is available and the source type is `generate`, generate a basic OpenAPI 3.0 schema from the codebase before creating the target.
            - Use the OpenAPI target creation flow for OpenAPI/Swagger input and the Postman target creation flow for Postman input.
            - If authentication is required, configure it after target creation using the workflow in the skill.

            Return:
            - Target ID
            - Final target name
            - Base URL
            - Source type used
            - Authentication status
            - Extra hosts added
            - Snyk API & Web link in this format: `https://plus.probely.app/targets/{{targetId}}`

            At the end, summarize the configured target in a table.
            """
            )
            .strip()
            .format(
                base_url=base_url,
                name=name,
                labels=labels,
                source_type=source_type,
                openapi_schema_url=openapi_schema_url,
                openapi_schema_content=openapi_schema_content,
                postman_collection_url=postman_collection_url,
                postman_collection_content=postman_collection_content,
                authentication=authentication,
                authentication_details=authentication_details,
            )
        )

    # Generic request tool to cover all API functionality
    @register_tool("probelyrequest")
    def probelyrequest(
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a raw request to Probely API (path relative to base).

        IMPORTANT: For authentication configuration, use probely_update_target instead:
        - HTTP Basic Auth: use basic_auth_username and basic_auth_password parameters
        - API Headers/Cookies Auth: use api_auth_headers and api_auth_cookies parameters

        This tool is for advanced use cases or API endpoints not covered by dedicated tools.

        When using this tool, reference saved credentials using the URI format
        'credentials://<credential_id>' (e.g., 'credentials://4DY4qGohso1r').
        Get credential URIs from probely_list_credentials or probely_create_credential.
        Do NOT use template syntax like {{cred-name}}."""
        return client.raw(
            method=method, path=path, params=params, json=json, data=data
        )

    # User Management (read-only)
    @register_tool("probely_get_user")
    def probely_get_user(userId: str) -> Dict[str, Any]:
        return client.get_user(user_id=userId)

    # Teams (read-only)
    @register_tool("probely_list_teams")
    def probely_list_teams(page: Optional[int] = None) -> Dict[str, Any]:
        return client.list_teams(page=page)

    @register_tool("probely_get_team")
    def probely_get_team(teamId: str) -> Dict[str, Any]:
        return client.get_team(team_id=teamId)

    # Credentials
    @register_tool("probely_list_credentials")
    def probely_list_credentials(
        page: Optional[int] = None,
        search: Optional[str] = None,
        is_sensitive: Optional[bool] = None,
        length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List credentials. Sensitive values are not returned.

        Returns credentials with their 'uri' field (e.g., 'credentials://4DY4qGohso1r').
        Use this exact URI format when configuring authentication (basic_auth, headers, etc.).
        Do NOT use template syntax like {{cred-name}}."""
        return client.list_credentials(
            page=page,
            search=search,
            is_sensitive=is_sensitive,
            length=length,
        )

    @register_tool("probely_get_credential")
    def probely_get_credential(credentialId: str) -> Dict[str, Any]:
        """Get a credential by ID. Value is null if sensitive.

        Returns the credential with its 'uri' field (e.g., 'credentials://4DY4qGohso1r').
        Use this URI to reference the credential in authentication configs."""
        return client.get_credential(credential_id=credentialId)

    @register_tool("probely_create_credential")
    def probely_create_credential(
        name: str,
        value: str,
        is_sensitive: bool = True,
        description: Optional[str] = None,
        team: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a credential for secure storage. Use is_sensitive=True for passwords.
        Returns the credential with id and uri. Use the uri (e.g. "credentials://xxxx") as the value in custom_field_mappings to link it to a sequence."""
        return client.create_credential(
            name=name,
            value=value,
            is_sensitive=is_sensitive,
            description=description,
            team=team,
        )

    @register_tool("probely_update_credential")
    def probely_update_credential(
        credentialId: str,
        name: Optional[str] = None,
        value: Optional[str] = None,
        is_sensitive: Optional[bool] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a credential (partial update)."""
        fields: Dict[str, Any] = {}
        if name is not None:
            fields["name"] = name
        if value is not None:
            fields["value"] = value
        if is_sensitive is not None:
            fields["is_sensitive"] = is_sensitive
        if description is not None:
            fields["description"] = description
        return client.update_credential(credential_id=credentialId, **fields)

    @register_tool("probely_delete_credential")
    def probely_delete_credential(credentialId: str) -> Dict[str, Any]:
        return client.delete_credential(credential_id=credentialId)

    # Labels
    @register_tool("probely_create_label")
    def probely_create_label(
        name: str, color: Optional[str] = None
    ) -> Dict[str, Any]:
        return client.create_label(name=name, color=color)

    # Targets
    @register_tool("probely_list_targets")
    def probely_list_targets(
        page: Optional[int] = None, search: Optional[str] = None
    ) -> Dict[str, Any]:
        return client.list_targets(page=page, search=search)

    @register_tool("probely_get_target")
    def probely_get_target(targetId: str) -> Dict[str, Any]:
        return client.get_target(target_id=targetId)

    @register_tool("probely_create_web_target")
    def probely_create_web_target(
        name: str,
        url: str,
        desc: Optional[str] = None,
        labels: Optional[list[str]] = None,
        scanning_agent_id: Optional[str] = None,
        allow_duplicate: bool = False,
    ) -> Dict[str, Any]:
        """Create a new target. Use labels to assign label names (e.g. ["Agentic", "Production"]).
        Existing labels are reused; missing ones are created automatically.
        Use scanning_agent_id to assign a scanning agent for internal/private targets.

        Set allow_duplicate=True to create a target even if another target with the same URL
        already exists. This is useful when you want multiple targets for the same URL with
        different configurations (e.g., different auth methods, different test scenarios).

        IMPORTANT: The response contains a top-level ``id`` (the target ID) and a nested
        ``site.id`` (the site ID). Always use the top-level ``id`` as the ``targetId``
        parameter for all subsequent tool calls (sequences, scans, logout detection, etc.).
        """
        return client.create_web_target(
            name=name,
            url=url,
            desc=desc,
            label_names=labels,
            default_label=target_defaults.get("default_label"),
            name_prefix=target_defaults.get("name_prefix", ""),
            scanning_agent_id=scanning_agent_id,
            allow_duplicate=allow_duplicate,
        )

    @register_tool("probely_update_target")
    def probely_update_target(
        targetId: str,
        name: Optional[str] = None,
        url: Optional[str] = None,
        desc: Optional[str] = None,
        labels: Optional[list[str]] = None,
        scanning_agent_id: Optional[str] = None,
        headers: Optional[List[Dict[str, str]]] = Field(
            default=None,
            description="Custom HTTP headers sent with every scan request (for general use, NOT for authentication). "
            'Each entry: {"name": "<header-name>", "value": "<header-value>"}. '
            "Replaces all existing custom headers. "
            "To reference saved credentials in header values, use URI format 'credentials://4DY4qGohso1r'. "
            "For API authentication using static headers, use api_auth_headers parameter instead.",
        ),
        cookies: Optional[List[Dict[str, str]]] = Field(
            default=None,
            description="Custom cookies sent with every scan request (for general use, NOT for authentication). "
            'Each entry: {"name": "<cookie-name>", "value": "<cookie-value>"}. '
            "Replaces all existing custom cookies. "
            "To reference saved credentials in cookie values, use URI format 'credentials://4DY4qGohso1r'. "
            "For API authentication using static cookies, use api_auth_cookies parameter instead.",
        ),
        basic_auth_username: Optional[str] = Field(
            default=None,
            description="Username for HTTP Basic Auth. Use credential URI format 'credentials://xxx' to reference saved credentials. "
            "When set, basic_auth_password must also be provided.",
        ),
        basic_auth_password: Optional[str] = Field(
            default=None,
            description="Password for HTTP Basic Auth. Use credential URI format 'credentials://xxx' to reference saved credentials. "
            "When set, basic_auth_username must also be provided.",
        ),
        api_auth_headers: Optional[List[Dict[str, Any]]] = Field(
            default=None,
            description="Authentication headers for API targets. Full structure with authentication flags. "
            'Each entry: {"name": "X-API-Key", "value": "credentials://xxx", "value_is_sensitive": false, '
            '"allow_testing": false, "authentication": true, "authentication_secondary": false}. '
            "Automatically sets api_login_enabled=true and api_login_method='headers_or_cookies'.",
        ),
        api_auth_cookies: Optional[List[Dict[str, Any]]] = Field(
            default=None,
            description="Authentication cookies for API targets. Full structure with authentication flags. "
            'Each entry: {"name": "session", "value": "credentials://xxx", "value_is_sensitive": false, '
            '"allow_testing": false, "authentication": true, "authentication_secondary": false}. '
            "Automatically sets api_login_enabled=true and api_login_method='headers_or_cookies'.",
        ),
    ) -> Dict[str, Any]:
        """Update a target. Use labels to assign label names (e.g. ["Agentic", "Production"]).
        Existing labels are reused; missing ones are created automatically.
        Use scanning_agent_id to assign or change the scanning agent. Pass "" to remove it.

        IMPORTANT: The headers/cookies parameters are for general custom headers/cookies sent with
        every scan request (NOT for authentication). They use a simple structure: {"name": "...", "value": "..."}.

        For HTTP Basic Auth authentication:
        Use basic_auth_username and basic_auth_password parameters. Both must be provided together.
        Example:
          probely_update_target(
            targetId,
            basic_auth_username="credentials://xxx",  # or inline: "api-user"
            basic_auth_password="credentials://yyy"   # or inline: "secret123"
          )

        For API authentication with static headers/cookies:
        Use api_auth_headers and/or api_auth_cookies parameters with full structure including authentication flags.
        The tool automatically sets api_login_enabled=true and api_login_method='headers_or_cookies'.
        Example:
          probely_update_target(
            targetId,
            api_auth_headers=[{
              "name": "X-API-Key",
              "value": "credentials://xxx",
              "value_is_sensitive": false,
              "allow_testing": false,
              "authentication": true,
              "authentication_secondary": false
            }],
            api_auth_cookies=[{
              "name": "session",
              "value": "credentials://yyy",
              "value_is_sensitive": false,
              "allow_testing": false,
              "authentication": true,
              "authentication_secondary": false
            }]
          )

        Reference saved credentials using URI format 'credentials://<credential_id>' (not {{cred-name}}).
        """
        fields: Dict[str, Any] = {}
        site_fields: Dict[str, Any] = {}

        if name is not None:
            site_fields["name"] = name
        if url is not None:
            site_fields["url"] = url
        if desc is not None:
            site_fields["desc"] = desc
        if headers is not None:
            site_fields["headers"] = headers
        if cookies is not None:
            site_fields["cookies"] = cookies

        # Handle API authentication headers/cookies
        if api_auth_headers is not None or api_auth_cookies is not None:
            # Add authentication headers/cookies to site_fields
            if api_auth_headers is not None:
                site_fields["headers"] = api_auth_headers
            if api_auth_cookies is not None:
                site_fields["cookies"] = api_auth_cookies

            # Set API scan settings for authentication
            api_scan_settings = site_fields.get("api_scan_settings", {})
            api_scan_settings.update(
                {
                    "api_login_enabled": True,
                    "api_headers_cookies_login_enabled_secondary": False,
                    "api_login_method": "headers_or_cookies",
                }
            )
            site_fields["api_scan_settings"] = api_scan_settings

        if site_fields:
            fields["site"] = site_fields
        if labels is not None:
            fields["labels"] = client.resolve_labels(labels)
        if scanning_agent_id is not None:
            fields["scanning_agent"] = (
                {"id": scanning_agent_id} if scanning_agent_id else None
            )

        # Handle HTTP Basic Auth
        if basic_auth_username is not None or basic_auth_password is not None:
            if basic_auth_username is None or basic_auth_password is None:
                return {
                    "error": {
                        "message": "Both basic_auth_username and basic_auth_password must be provided together"
                    }
                }
            fields["has_basic_auth"] = True
            fields["basic_auth"] = {
                "username": basic_auth_username,
                "password": basic_auth_password,
            }

        return client.update_target(target_id=targetId, **fields)

    @register_tool("probely_delete_target")
    def probely_delete_target(targetId: str) -> Dict[str, Any]:
        return client.delete_target(target_id=targetId)

    # Login Sequences
    @register_tool("probely_list_sequences")
    def probely_list_sequences(
        targetId: str, page: Optional[int] = None
    ) -> Dict[str, Any]:
        """List all login sequences for a target."""
        return client.list_sequences(target_id=targetId, page=page)

    @register_tool("probely_get_sequence")
    def probely_get_sequence(targetId: str, sequenceId: str) -> Dict[str, Any]:
        """Get details of a specific login sequence."""
        return client.get_sequence(target_id=targetId, sequence_id=sequenceId)

    @register_tool("probely_create_sequence")
    def probely_create_sequence(
        targetId: str,
        name: str,
        content: str,
        sequence_type: str = "login",
        enabled: bool = True,
        custom_field_mappings: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Create a login sequence. Content must be a JSON string of the sequence steps array. Use custom_field_mappings to configure credentials.

        Use credentials management by default: link a credential (created via probely_create_credential) for the password. If the user explicitly declines, inline values are allowed.
        - Password credential: [{"name": "[CUSTOM_PASSWORD]", "value": "credentials://<credential_id>", "value_is_sensitive": true, "enabled": true}]
        - When multiple targets share the same credential and it already exists and is_sensitive=True, prompt the user to deobfuscate it in order to allow reuse.

        For username: [{"name": "[CUSTOM_USERNAME]", "value": "user@example.com", "value_is_sensitive": true, "enabled": true}]
        """
        mappings = _parse_list_of_dicts(custom_field_mappings)
        return client.create_sequence(
            target_id=targetId,
            name=name,
            sequence_type=sequence_type,
            content=content,
            enabled=enabled,
            custom_field_mappings=mappings,
        )

    @register_tool("probely_update_sequence")
    def probely_update_sequence(
        targetId: str,
        sequenceId: str,
        name: Optional[str] = None,
        content: Optional[str] = None,
        enabled: Optional[bool] = None,
        custom_field_mappings: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Update a login sequence. Use custom_field_mappings to configure credentials instead of hardcoding them in the sequence content. Use credential URIs for sensitive values by default.

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
        return client.update_sequence(
            target_id=targetId, sequence_id=sequenceId, **fields
        )

    @register_tool("probely_delete_sequence")
    def probely_delete_sequence(
        targetId: str, sequenceId: str
    ) -> Dict[str, Any]:
        return client.delete_sequence(
            target_id=targetId, sequence_id=sequenceId
        )

    # Authentication Configuration
    @register_tool("probely_configure_form_login")
    def probely_configure_form_login(
        targetId: str,
        login_url: str,
        username_field: str,
        password_field: str,
        username: str,
        password: str,
        check_pattern: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Configure form-based login authentication. Only use this as a fallback when Playwright is NOT available. When Playwright IS available, always record a login sequence instead (probely_create_sequence).

        To reference saved credentials, use URI format 'credentials://<credential_id>' (e.g., 'credentials://4DY4qGohso1r').
        Get credential URIs from probely_list_credentials or probely_create_credential."""
        return client.configure_form_login(
            target_id=targetId,
            login_url=login_url,
            username_field=username_field,
            password_field=password_field,
            username=username,
            password=password,
            check_pattern=check_pattern,
        )

    @register_tool("probely_configure_sequence_login")
    def probely_configure_sequence_login(
        targetId: str, enabled: bool = True
    ) -> Dict[str, Any]:
        """Enable or disable sequence-based login. Call this after creating a login sequence."""
        return client.configure_sequence_login(
            target_id=targetId, enabled=enabled
        )

    @register_tool("probely_configure_2fa_totp")
    def probely_configure_2fa_totp(
        targetId: str,
        otp_secret: str,
        otp_algorithm: str = "SHA1",
        otp_digits: int = 6,
    ) -> Dict[str, Any]:
        """Configure TOTP-based 2FA for a target. Automatically generates a TOTP code from the
        secret and configures it as the OTP placeholder for the login sequence.

        Call this BEFORE creating/updating the login sequence. The response includes an
        ``otp_code`` field — use this exact code hardcoded in the sequence's fill_value step
        for the OTP input. Probely will auto-convert that step to ``fill_otp`` at scan time.
        """
        totp = _generate_totp(
            otp_secret, algorithm=otp_algorithm, digits=otp_digits
        )
        result = client.configure_2fa(
            target_id=targetId,
            otp_secret=otp_secret,
            otp_placeholder=totp["code"],
            otp_algorithm=otp_algorithm,
            otp_digits=otp_digits,
            otp_type="totp",
        )
        result["otp_code"] = totp["code"]
        return result

    @register_tool("probely_disable_2fa")
    def probely_disable_2fa(targetId: str) -> Dict[str, Any]:
        """Disable 2FA/OTP for a target."""
        return client.disable_2fa(target_id=targetId)

    @register_tool("probely_generate_totp")
    def probely_generate_totp(
        secret: str, algorithm: str = "SHA1", digits: int = 6, period: int = 30
    ) -> Dict[str, Any]:
        """Generate a TOTP code from a secret/seed. Use this when recording login sequences that require 2FA.
        Returns the current TOTP code and its remaining validity in seconds."""
        return _generate_totp(
            secret, algorithm=algorithm, digits=digits, period=period
        )

    @register_tool("probely_list_logout_detectors")
    def probely_list_logout_detectors(targetId: str) -> Dict[str, Any]:
        """List all logout detectors for a target."""
        return client.list_logout_detectors(target_id=targetId)

    @register_tool("probely_create_logout_detector")
    def probely_create_logout_detector(
        targetId: str, detector_type: str, value: str
    ) -> Dict[str, Any]:
        """Create a logout detector for a target.

        Args:
            targetId: The target ID
            detector_type: Type of detector - 'text' (text that appears after logout),
                          'url' (redirect URL after logout), or 'sel' (CSS selector after logout)
            value: The value for the detector (e.g., "Login", "/login", ".login-form")
        """
        return client.create_logout_detector(
            target_id=targetId, detector_type=detector_type, value=value
        )

    @register_tool("probely_configure_logout_detection")
    def probely_configure_logout_detection(
        targetId: str,
        enabled: bool = True,
        check_session_url: Optional[str] = None,
        logout_detector_type: Optional[str] = None,
        logout_detector_value: Optional[str] = None,
        logout_condition: Optional[str] = None,
    ) -> Dict[str, Any]:
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
            logout_condition=logout_condition,
        )

    # Extra Hosts
    @register_tool("probely_list_extra_hosts")
    def probely_list_extra_hosts(
        targetId: str, page: Optional[int] = None
    ) -> Dict[str, Any]:
        return client.list_extra_hosts(target_id=targetId, page=page)

    @register_tool("probely_get_extra_host")
    def probely_get_extra_host(
        targetId: str, extraHostId: str
    ) -> Dict[str, Any]:
        return client.get_extra_host(
            target_id=targetId, extra_host_id=extraHostId
        )

    @register_tool("probely_create_extra_host")
    def probely_create_extra_host(
        targetId: str, hostname: str, ip_address: str
    ) -> Dict[str, Any]:
        return client.create_extra_host(
            target_id=targetId, hostname=hostname, ip_address=ip_address
        )

    @register_tool("probely_update_extra_host")
    def probely_update_extra_host(
        targetId: str,
        extraHostId: str,
        hostname: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}
        if hostname is not None:
            fields["hostname"] = hostname
        if ip_address is not None:
            fields["ip_address"] = ip_address
        return client.update_extra_host(
            target_id=targetId, extra_host_id=extraHostId, **fields
        )

    @register_tool("probely_delete_extra_host")
    def probely_delete_extra_host(
        targetId: str, extraHostId: str
    ) -> Dict[str, Any]:
        return client.delete_extra_host(
            target_id=targetId, extra_host_id=extraHostId
        )

    # Scans
    @register_tool("probely_list_scans")
    def probely_list_scans(
        targetId: str, page: Optional[int] = None
    ) -> Dict[str, Any]:
        return client.list_scans(target_id=targetId, page=page)

    @register_tool("probely_get_scan")
    def probely_get_scan(targetId: str, scanId: str) -> Dict[str, Any]:
        return client.get_scan(target_id=targetId, scan_id=scanId)

    @register_tool("probely_start_scan")
    def probely_start_scan(
        targetId: str, profile: Optional[str] = None
    ) -> Dict[str, Any]:
        return client.start_scan(target_id=targetId, profile=profile)

    @register_tool("probely_stop_scan")
    def probely_stop_scan(targetId: str, scanId: str) -> Dict[str, Any]:
        return client.stop_scan(target_id=targetId, scan_id=scanId)

    @register_tool("probely_cancel_scan")
    def probely_cancel_scan(targetId: str, scanId: str) -> Dict[str, Any]:
        return client.cancel_scan(target_id=targetId, scan_id=scanId)

    # Findings
    @register_tool("probely_list_findings")
    def probely_list_findings(
        targetId: str,
        page: Optional[int] = None,
        severity: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        return client.list_findings(
            target_id=targetId, page=page, severity=severity, state=state
        )

    @register_tool("probely_get_finding")
    def probely_get_finding(targetId: str, findingId: str) -> Dict[str, Any]:
        return client.get_finding(target_id=targetId, finding_id=findingId)

    @register_tool("probely_update_finding")
    def probely_update_finding(
        targetId: str,
        findingId: str,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        return client.update_finding(
            target_id=targetId, finding_id=findingId, state=state
        )

    @register_tool("probely_bulk_update_findings")
    def probely_bulk_update_findings(
        targetId: str,
        findingIds: list[str],
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Bulk update finding states (e.g. fixed, false_positive, accepted_risk).
        This tool will automatically ask the user for confirmation."""
        return client.bulk_update_findings(
            target_id=targetId, finding_ids=findingIds, state=state
        )

    # Settings
    @register_tool("probely_get_target_settings")
    def probely_get_target_settings(targetId: str) -> Dict[str, Any]:
        return client.get_target_settings(target_id=targetId)

    @register_tool("probely_update_target_settings")
    def probely_update_target_settings(
        targetId: str,
        excluded_paths: Optional[list[str]] = None,
        max_scan_duration: Optional[int] = None,
        scan_profile: Optional[str] = None,
    ) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}

        if excluded_paths is not None:
            fields["excluded_paths"] = excluded_paths
        if max_scan_duration is not None:
            fields["max_scan_duration"] = max_scan_duration
        if scan_profile is not None:
            fields["scan_profile"] = scan_profile
        return client.update_target_settings(target_id=targetId, **fields)

    # Reports (using top-level /report/ endpoint)
    @register_tool("probely_create_scanreport")
    def probely_create_scanreport(
        scanId: str,
        report_type: str = "default",
        format: str = "pdf",
    ) -> Dict[str, Any]:
        """Create a report for a scan. Returns report metadata including the report ID.

        Args:
            scanId: The scan ID to generate the report for
            report_type: Type of report - "default", "executive", "owasp", "pci", "hipaa", "iso27001"
            format: File format - "pdf" or "html"
        """
        return client.create_scanreport(
            scan_id=scanId, report_type=report_type, report_format=format
        )

    @register_tool("probely_downloadreport")
    def probely_downloadreport(reportId: str) -> Dict[str, Any]:
        """Download a report by its ID."""
        status, body = client.downloadreport(report_id=reportId)
        return {"status": status, **body}

    @register_tool("probely_getreport")
    def probely_getreport(reportId: str) -> Dict[str, Any]:
        """Get report metadata/status by ID."""
        return client.getreport(report_id=reportId)

    # Scanning Agents
    @register_tool("probely_list_scanning_agents")
    def probely_list_scanning_agents(
        page: Optional[int] = None,
        length: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List scanning agents. Use status to filter: 'connected', 'connected_with_issues', 'disconnected'."""
        return client.list_scanning_agents(
            page=page, length=length, status=status, search=search
        )

    @register_tool("probely_get_scanning_agent")
    def probely_get_scanning_agent(agentId: str) -> Dict[str, Any]:
        """Get details of a specific scanning agent."""
        return client.get_scanning_agent(agent_id=agentId)

    def _fetchjson_or_url(
        url: Optional[str], json_body: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Fetch JSON/YAML from a URL, or return the provided object as-is."""
        if json_body is not None:
            return json_body
        if url:
            import requests as requests

            r = requests.get(url, timeout=60)
            r.raise_for_status()
            content_type = r.headers.get("Content-Type", "")
            if "yaml" in content_type or url.endswith((".yaml", ".yml")):
                import yaml

                return yaml.safe_load(r.text)
            return r.json()
        return None

    # API Target from Postman
    @register_tool("probely_create_api_target_from_postman")
    def probely_create_api_target_from_postman(
        name: str,
        target_url: str,
        postman_collection_url: Optional[str] = None,
        postman_collectionjson: Optional[Dict[str, Any]] = None,
        desc: Optional[str] = None,
        labels: Optional[list[str]] = None,
        allow_duplicate: bool = False,
    ) -> Dict[str, Any]:
        """Create an API target from a Postman collection. Provide either postman_collection_url or postman_collectionjson.

        Set allow_duplicate=True to create a target even if another target with the same URL
        already exists. This is useful when you want multiple targets for the same URL with
        different configurations (e.g., different auth methods, different test scenarios).

        IMPORTANT: The response contains a top-level ``id`` (the target ID) and a nested
        ``site.id`` (the site ID). Always use the top-level ``id`` as the ``targetId``
        parameter for all subsequent tool calls (update_target, start_scan, etc.).
        Do NOT use the nested ``site.id`` field for target operations."""
        collection = _fetchjson_or_url(
            postman_collection_url, postman_collectionjson
        )
        if not collection:
            return {
                "error": {
                    "message": "Provide postman_collection_url or postman_collectionjson"
                }
            }
        return client.create_api_target(
            name=name,
            target_url=target_url,
            schema_type="postman",
            schema=collection,
            desc=desc,
            label_names=labels,
            default_label=target_defaults.get("default_label"),
            name_prefix=target_defaults.get("name_prefix", ""),
            allow_duplicate=allow_duplicate,
        )

    # API Target from OpenAPI
    @register_tool("probely_create_api_target_from_openapi")
    def probely_create_api_target_from_openapi(
        name: str,
        target_url: str,
        openapi_schema_url: Optional[str] = None,
        openapi_schemajson: Optional[Dict[str, Any]] = None,
        desc: Optional[str] = None,
        labels: Optional[list[str]] = None,
        allow_duplicate: bool = False,
    ) -> Dict[str, Any]:
        """Create an API target from an OpenAPI/Swagger schema. Provide either openapi_schema_url or openapi_schemajson. When the user provides openapi_schema_url, do not fetch the openapi_schemajson from that url.

        Set allow_duplicate=True to create a target even if another target with the same URL
        already exists. This is useful when you want multiple targets for the same URL with
        different configurations (e.g., different auth methods, different test scenarios).

        IMPORTANT: The response contains a top-level ``id`` (the target ID) and a nested
        ``site.id`` (the site ID). Always use the top-level ``id`` as the ``targetId``
        parameter for all subsequent tool calls (update_target, start_scan, etc.).
        Do NOT use the nested ``site.id`` field for target operations."""
        if not openapi_schema_url and not openapi_schemajson:
            return {
                "error": {
                    "message": "Provide openapi_schema_url or openapi_schemajson"
                }
            }
        if openapi_schema_url:
            return client.create_api_target(
                name=name,
                target_url=target_url,
                schema_type="openapi",
                schema=None,
                api_schema_url=openapi_schema_url,
                desc=desc,
                label_names=labels,
                default_label=target_defaults.get("default_label"),
                name_prefix=target_defaults.get("name_prefix", ""),
                allow_duplicate=allow_duplicate,
            )
        schema = _fetchjson_or_url(None, openapi_schemajson)
        if not schema:
            return {"error": {"message": "Could not use openapi_schemajson"}}
        return client.create_api_target(
            name=name,
            target_url=target_url,
            schema_type="openapi",
            schema=schema,
            desc=desc,
            label_names=labels,
            default_label=target_defaults.get("default_label"),
            name_prefix=target_defaults.get("name_prefix", ""),
            allow_duplicate=allow_duplicate,
        )

    return app
