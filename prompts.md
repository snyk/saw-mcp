# Snyk API & Web MCP Server — Example Prompts

A collection of ready-to-use prompts, from quick one-liners to detailed multi-target configurations.

---

## Target Creation

### Simple

```
Add target example.com
```

```
Create a target for https://staging.myapp.io and label it "Staging"
```

```
Add target shop.example.com with credentials admin@shop.com / s3cretPass
```

### With 2FA

```
Add target secure.example.com with credentials admin@secure.com / hunter2 and TOTP seed JBSWY3DPEHPK3PXP
```

### Named and labeled

```
Create a target named "Customer Portal" for https://portal.acme.com, label it "Production" and "Critical"
```

### With scanning agent (internal targets)

```
Add an internal target https://10.0.1.50:8443 named "Internal Admin Panel" using scanning agent "office-scanner"
```

---

## Multi-Target Onboarding

```
Add these targets:
- app1.example.com (user1@example.com / pass1)
- app2.example.com (user2@example.com / pass2)
- app3.example.com (user3@example.com / pass3, TOTP seed JBSWY3DPEHPK3PXP)
```

```
Onboard these three apps, all labeled "Sprint-42":
1. https://crm.acme.com — sales@acme.com / CrmPass!99
2. https://hr.acme.com — admin@hr.acme.com / HrSecure#21
3. https://finance.acme.com — auditor@acme.com / FinAudit$7 — TOTP seed NBSWY3DPEHPK3PXQ
```

```
Add these targets with custom names:
- "Checkout Flow" at https://checkout.shop.io (buyer@shop.io / shopPass1)
- "Merchant Dashboard" at https://merchant.shop.io (merchant@shop.io / merchPass2)
```

---

## API Targets

### From OpenAPI / Swagger

```
Create an API target from this OpenAPI schema: https://petstore.swagger.io/v2/swagger.json
```

```
Add an API target for https://api.myservice.com using the OpenAPI spec at ./docs/openapi.yaml
```

### From Postman collection

```
Create an API target from this Postman collection: https://www.getpostman.com/collections/abc123def456
```

```
Add an API target named "Payments API" from the Postman collection in ./postman/payments.json, target URL https://api.payments.example.com
```

### Generated from codebase

```
Scan this project for API endpoints, generate an OpenAPI schema, and create a Snyk API & Web API target for https://api.myapp.com
```

---

## Authentication Configuration

### Form login (no browser available)

```
Configure form login on target BtJpAVjqZjXP:
- Login URL: https://app.example.com/login
- Username field: input[name="email"]
- Password field: input[name="password"]
- Username: admin@example.com
- Password: secret123
```

### Record a login sequence (browser available)

```
Record a login sequence for target BtJpAVjqZjXP by navigating to https://app.example.com/login, filling in admin@example.com / secret123, and submitting the form
```

### Configure 2FA on existing target

```
Enable TOTP 2FA on target BtJpAVjqZjXP with seed JBSWY3DPEHPK3PXP
```

### Disable 2FA

```
Disable 2FA on target BtJpAVjqZjXP
```

---

## Logout Detection

```
Enable logout detection on target BtJpAVjqZjXP using the post-login URL https://app.example.com/dashboard
```

```
Configure logout detection on target BtJpAVjqZjXP:
- Session check URL: https://app.example.com/settings
- Detector: CSS selector input[name="email"]
- Condition: any
```

```
Set up logout detection on target BtJpAVjqZjXP with a text-based detector that looks for "Sign In" on the page
```

---

## Scanning

### Start

```
Start a scan on target BtJpAVjqZjXP
```

```
Run a full scan on target BtJpAVjqZjXP
```

```
Start a lightning scan on target BtJpAVjqZjXP
```

```
Scan target BtJpAVjqZjXP with the safe profile
```

### Monitor

```
What's the status of the latest scan on target BtJpAVjqZjXP?
```

```
List all running scans
```

```
Show me the scan history for target BtJpAVjqZjXP
```

### Stop / Cancel

```
Stop the scan running on target BtJpAVjqZjXP
```

```
Cancel all running scans
```

---

## Findings & Vulnerabilities

### List

```
Show me all findings for target BtJpAVjqZjXP
```

```
List high and critical findings for target BtJpAVjqZjXP
```

```
What vulnerabilities were found on target BtJpAVjqZjXP? Show only unfixed ones sorted by severity
```

### Inspect

```
Show me the details of finding abc123 on target BtJpAVjqZjXP
```

```
Explain finding abc123 on target BtJpAVjqZjXP and suggest a fix
```

### Triage

```
Mark finding abc123 on target BtJpAVjqZjXP as accepted risk
```

```
Mark finding abc123 as fixed on target BtJpAVjqZjXP
```

```
Bulk-mark all low-severity findings on target BtJpAVjqZjXP as accepted risk
```

---

## Credentials Management

```
Create a credential named "CI Bot Password" with value "s3cret" (sensitive)
```

```
List all stored credentials
```

```
Update credential 2UGnMkoLoeyn with a new password value
```

```
Delete credential 2UGnMkoLoeyn
```

---

## Login Sequences

```
List all login sequences for target BtJpAVjqZjXP
```

```
Show me the details of sequence xyz789 on target BtJpAVjqZjXP
```

```
Disable the login sequence on target BtJpAVjqZjXP
```

```
Update the login sequence on target BtJpAVjqZjXP to use new credentials admin@newdomain.com / newPass456
```

---

## Extra Hosts

```
Add api.example.com as an extra host on target BtJpAVjqZjXP
```

```
List all extra hosts for target BtJpAVjqZjXP
```

```
Detect and add any API hosts used by target BtJpAVjqZjXP
```

```
Remove extra host xyz789 from target BtJpAVjqZjXP
```

---

## Reports

```
Generate a PDF scan report for the latest scan on target BtJpAVjqZjXP
```

```
Download the report for scan abc123 on target BtJpAVjqZjXP
```

---

## Target Management

### List and search

```
List all my targets
```

```
Search for targets matching "staging"
```

```
Show me all targets labeled "Production"
```

### Inspect

```
Show me the full config of target BtJpAVjqZjXP
```

```
What authentication is configured on target BtJpAVjqZjXP?
```

```
Show the target settings for BtJpAVjqZjXP
```

### Update

```
Rename target BtJpAVjqZjXP to "Production App v2"
```

```
Change the scan profile on target BtJpAVjqZjXP to "full"
```

```
Add label "PCI" to target BtJpAVjqZjXP
```

### Delete

```
Delete target BtJpAVjqZjXP
```

---

## Labels

```
Create a label called "PCI-DSS"
```

```
Create labels "Production", "Staging", and "Development"
```

---

## Teams & Users

```
List all teams
```

```
Show me the details of my user account
```

```
Which team does target BtJpAVjqZjXP belong to?
```

---

## Scanning Agents

```
List all available scanning agents
```

```
Show me the details of scanning agent xyz789
```

```
Which scanning agent is assigned to target BtJpAVjqZjXP?
```

---

## Complex Multi-Step Workflows

### Full onboarding with post-scan triage

```
Do the following end-to-end:
1. Create a target for https://app.acme.com with credentials admin@acme.com / AcmePass!42
2. Record the login sequence and configure logout detection
3. Detect and add any API extra hosts
4. Start a normal scan
5. Once the scan finishes, list all high/critical findings and explain each one
```

### Migrate and re-scan

```
I have an existing target BtJpAVjqZjXP but the app moved to https://v2.app.example.com.
Create a new target for the new URL with the same credentials (admin@example.com / Pass!word99),
configure authentication, and start a scan.
```

### Security audit across environments

```
Set up and scan all three environments for our app:
1. "Acme Dev" — https://dev.acme.com (dev@acme.com / devPass1) — label "Dev"
2. "Acme Staging" — https://staging.acme.com (qa@acme.com / qaPass2) — label "Staging"
3. "Acme Prod" — https://app.acme.com (admin@acme.com / prodPass3, TOTP seed HXDMVJECJJWSRB3HWIZR4IFUGFTMXBOZ) — label "Production"

After all three are onboarded, start a normal scan on each.
```

### API + Web combined

```
Our service has two parts:
1. A web frontend at https://app.example.com (user@example.com / frontPass1)
2. A REST API at https://api.example.com with this OpenAPI spec: ./docs/api.yaml

Create both targets, configure auth on the web target, and start scans on both.
```

### Findings comparison across scans

```
Compare the findings from the last two scans on target BtJpAVjqZjXP.
Show me which vulnerabilities are new, which were fixed, and which persist.
```

### Bulk credential rotation

```
The password for all our test accounts changed to "NewGlobalPass!2026".
Update the credentials on these targets:
- BtJpAVjqZjXP (jane@example.com)
- CkLmNoPqRsT (admin@example.com)
- DwXyZaBcDeF (tester@example.com)
```

### Report generation for compliance

```
For each target labeled "PCI-DSS":
1. List the target name and URL
2. Show the count of open high/critical findings
3. Generate a PDF report from the latest scan
```

### Onboard from codebase context

```
Look at this project's codebase, figure out the deployed URL and any API endpoints,
then create the appropriate Snyk API & Web targets and configure them for scanning.
```
