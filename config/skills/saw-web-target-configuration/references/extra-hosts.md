# Detecting and Configuring Extra Hosts

Extra host detection is **CRITICAL** — missing an API host means the scanner cannot test those endpoints. Use a **multi-layered approach** with retries and fallbacks to ensure no hosts are missed.

## Layer 1: Network request capture (primary method, with retries)

Capture network requests at **two checkpoints** during the login flow, while the browser session is still active:

1. **After initial page navigation** (before login) — run `playwright-cli -s=SESSION network` right after navigating to the target URL and the login page loads. Some apps make API calls on page load.
2. **After login completes** — run `playwright-cli -s=SESSION network` again after successful login. If the post-login landing page is minimal, navigate to a content page (e.g. `/dashboard`, `/wines`, `/home`) that loads the app's main data, then run `network` again.

**If `network` fails at any checkpoint, retry it up to 2 more times** (3 attempts total). Take a `playwright-cli -s=SESSION snapshot` between retries to re-stabilize the session. Do NOT skip this step on failure — exhaust all retries first.

From the collected requests, extract hostnames and compare against the target's primary hostname. Apps may use microservices on different domains, so include all application-related hosts — not just same-domain ones.

## Layer 2: JavaScript introspection (fallback)

**Always run this as a secondary check**, even if Layer 1 succeeded. Use `playwright-cli -s=SESSION eval` on the post-login page to discover API base URLs embedded in the page's JavaScript context using `scripts/extract-api-hosts.js`.

Merge the results from Layer 2 with any hosts found in Layer 1.

## Filtering and adding extra hosts

From the combined results of both layers:
- **Include** all application-related hostnames, even if they are on different domains (microservices, separate API backends, auth services, etc.).
- **Exclude** only well-known third-party infrastructure/vendor hostnames (e.g., `cdn.jsdelivr.net`, `fonts.googleapis.com`, `analytics.google.com`, `cdn.cloudflare.com`).

For each relevant hostname found:
```python
probely_create_extra_host(targetId, hostname="api.example.com", ip_address="")
```

**Always report** what was detected: "Detected API calls to `api.example.com`. Added as extra host."

If both layers returned zero extra hosts, report: "No external API hosts detected (checked via network requests and JS introspection)."
