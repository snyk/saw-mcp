---
description: Snyk API&Web (SAW) behavioral rules - safety constraints, proactive monitoring, and vulnerability handling.
alwaysApply: true
---

# Snyk API&Web (SAW) Project Rules

These rules define behavioral constraints and proactive behaviors for projects using SAW.

## CRITICAL: Always Use the SAW MCP Server

**For ANY task involving Snyk API&Web, SAW, or Probely, you MUST use the SAW MCP Server tools.**

- Do NOT attempt to call the Snyk API&Web REST API directly via HTTP requests
- Do NOT write code that makes API calls to api.probely.com
- ALWAYS use the `probely_*` MCP tools provided by the SAW MCP server
- The SAW MCP server handles authentication, retries, and error handling for you

### If a `probely_*` tool call fails, fix the parameters and retry

NEVER work around MCP tool failures by:
- Writing Python/shell scripts to call the Probely API directly
- Using curl or any HTTP client as a substitute
- Creating helper files to generate or fix payloads

The MCP tools handle formatting (e.g., pretty-printing login sequences). Bypassing them loses that.

### Trigger Keywords

Use SAW MCP tools when the user mentions any of:
- "Snyk API&Web" / "Snyk APIWeb" / "Snyk API Web"
- "SAW" (when referring to security scanning)
- "Probely" (legacy name)
- "DAST" / "Dynamic Application Security Testing"
- "security scan" / "vulnerability scan" / "web scan"
- "target" (in security scanning context)
- "findings" / "vulnerabilities" (from scans)

## Automatic Target Discovery

When a new project is loaded or workspace is opened, check if it's an **application or API codebase** (look for indicators like web frameworks, API routes, package.json with web dependencies, etc.). 

**Only for app/API projects:**
- Search for corresponding SAW targets using `probely_list_targets` with the project name or domain
- If a matching target is found, inform the user about existing security testing coverage
- If no target is found, suggest creating a new SAW target for the project

**Skip this for non-app projects** (libraries, CLI tools, documentation, etc.).

## NEVER Start Scans Automatically

**IMPORTANT: NEVER start a scan automatically.** Scans are intrusive and could potentially affect the target system.

- Only start scans when the user explicitly requests it
- Explain that scans should only be run against systems the user has permission to test
- Recommend starting with a quick scan profile first to verify authentication works

## Vulnerability Remediation

When high-risk or critical vulnerabilities are identified from scans:

1. **DO NOT** modify the codebase directly.
2. Use `probely_get_finding` to retrieve detailed vulnerability information including:
   - Vulnerability description
   - CVSS score and severity
   - Affected endpoints/paths
   - Fix recommendations
3. Create a **patch file** or **fix proposal document** that contains:
   - The vulnerable code (with clear markers)
   - The recommended fix
   - Explanation of the security issue
   - References to security advisories or CWE entries
4. Save the patch/fix as a separate file (e.g., `saw-security-fix.patch` or `SECURITY_FIXES.md`)
5. **Alert the user** about the vulnerabilities found and the location of the patch file
6. Allow the user to review and apply fixes manually

## Security Scan Recommendations

- When working on security-sensitive code, suggest running SAW scans using `probely_start_scan`.
- Review findings using `probely_list_findings` with severity filters for high/critical issues.

## Active Scan Monitoring

**If a scan is running** for the project's SAW target:

1. Check scan progress every 5 minutes using `probely_get_scan` or `probely_list_scans`.
2. Display progress with delta from previous check:
   - Progress percentage and change (e.g., "45% complete (+5% since last check)")
   - Estimated time remaining
   - New vulnerabilities found since last check
   - Severity breakdown
3. If scan completes, alert the user and offer to:
   - List all findings using `probely_list_findings`
   - Generate a report using `probely_create_report`
   - Analyze high-risk/critical vulnerabilities for remediation

## Finding Management

Use `probely_update_finding` or `probely_bulk_update_findings` to mark findings as:
- `fixed` - after the user has applied the fix
- `false_positive` - if verified as not exploitable
- `accepted_risk` - with user approval for business-justified risks

## Multiple Targets: Use Subagents in Parallel

When the user asks to add, configure, or onboard **more than one** SAW target in a single request, you **MUST** launch a separate `generalPurpose` subagent for each target via the Task tool.

**CRITICAL: All Task tool calls MUST be in a single assistant message.** Keep each subagent prompt short (target details + instruction to read the skill file). Do NOT embed the full skill text in each prompt — that makes the message too large and causes sequential execution. Each subagent reads the skill file itself.

### Subagent workspace discipline

Subagents configuring SAW targets must NOT grep or search the local workspace for patterns (e.g., searching for "OTP" examples in project source files). The workspace content is unrelated to target configuration. All necessary context must come from the task prompt and the MCP tool responses.

## Reporting

Generate security reports using `probely_create_report` when:
- Multiple vulnerabilities are fixed
- Before major releases
- For compliance documentation
