# Security

## Reporting Security Issues

If you believe you have found a security vulnerability in this project, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please report security issues via:

<https://docs.snyk.io/snyk-data-and-governance/reporting-security-issues>

## Data handling and classification

The SAW MCP server is **external tooling**: it runs in the user's own
environment (their IDE, agent host, or shell) and talks to the Snyk API & Web
platform (`api.probely.com`). It is not a hosted Snyk service, so it does not
persist any of the data below to Snyk-managed storage — data is held in memory
for the lifetime of a request and forwarded to the Snyk API & Web platform,
where the platform's own controls apply.

The tool nevertheless handles highly sensitive data. The table below records
each data source, what it is, and its data-classification level (DCL) so that
logging, storage, and access controls can be aligned with it.

| Data source / flow | Examples | Classification | Where it lives |
|---|---|---|---|
| Snyk API & Web API key | `MCP_SAW_API_KEY`, config `api_key`, `op://` / `env:` secret references | **DCL4** | Env var, `.env` (gitignored), or `config/config.yaml` (gitignored); sent as the `Authorization: JWT …` request header. Resolved at runtime when a secret reference is used. |
| Customer web-application login credentials | Usernames/passwords supplied for target login sequences and form login | **DCL6** | Passed as tool arguments in memory, forwarded to the platform, and stored there as Probely credentials (marked sensitive). Not persisted by the MCP server. |
| 2FA / TOTP secrets | `otp_secret`, `totp_seed` used to generate one-time codes | **DCL4** | In memory for OTP generation and forwarded to the platform. Not persisted by the MCP server. |
| DAST scan findings | Vulnerability details, evidence, affected URLs returned by scans | **DCL4** | Fetched from the platform and returned to the AI client on request. Not persisted by the MCP server. |

DCL4 = highly confidential / secrets. DCL6 = customer secrets subject to the
strictest handling requirements. The highest level handled is recorded as
`DCL6` in [`catalog-info.yaml`](catalog-info.yaml).

### Logging and redaction

Logs are written to `~/saw-mcp.log` (rotating, 50 MB × 3 backups) and to the
console. Log level defaults to `INFO` and is controlled by
`MCP_SAW_LOG_LEVEL`.

To keep DCL4+ data out of logs:

- **The API key is never logged.** It is only ever set on the HTTP session's
  `Authorization` header; request/response logging does not include headers.
- **Request and response bodies are redacted before logging.** At `DEBUG`
  level the client logs outgoing request bodies and incoming responses; before
  they are written, values for secret-bearing keys — passwords, credential
  values, TOTP/OTP seeds, tokens, API keys, `Authorization`, and login-sequence
  content — are replaced with `***REDACTED***`. See `_redact_for_log` in
  [`snyk_apiweb/probely_client.py`](snyk_apiweb/probely_client.py).
- **`DEBUG` logging is opt-in.** Verbose logging is only produced when
  `MCP_SAW_LOG_LEVEL=DEBUG` is set explicitly.

When adding new tools or client methods that carry credentials, secrets, or
other DCL4+ values, make sure any new sensitive field name is covered by the
redaction key set so it does not leak into the debug log.
