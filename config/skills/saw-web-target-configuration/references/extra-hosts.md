# Detecting and Configuring Extra Hosts

Extra host detection is **CRITICAL** — missing an API host means the scanner cannot test those endpoints. Use a **multi-layered approach** with retries and fallbacks to ensure no hosts are missed.

## Layer 1: Network request capture (primary method, with retries)

Capture network requests at **two checkpoints** during the login flow:

1. **After initial page navigation** (before login) — call `browser_network_requests()` right after navigating to the target URL and the login page loads. Some apps make API calls on page load.
2. **After login completes** — call `browser_network_requests()` again after successful login. Login and post-login pages often trigger additional API calls.

**If `browser_network_requests()` fails at any checkpoint, retry it up to 2 more times** (3 attempts total). Take a `browser_snapshot` between retries to re-stabilize the session. Do NOT skip this step on failure — exhaust all retries first.

From the collected requests, extract hostnames and compare against the target's primary hostname. Common patterns:
- `api.example.com` vs `app.example.com` or `example.com`
- `auth.example.com` vs `www.example.com`
- `backend.example.com` vs `example.com`

## Layer 2: JavaScript introspection (fallback)

**Always run this as a secondary check**, even if Layer 1 succeeded. Use `browser_evaluate` on the post-login page to discover API base URLs embedded in the page's JavaScript context using `scripts/extract-api-hosts.js`.

Merge the results from Layer 2 with any hosts found in Layer 1.

## Filtering and adding extra hosts

From the combined results of both layers:
- **Include** hostnames that share the same base domain as the target (e.g., `api.example.com` for a target at `example.com`).
- **Exclude** unrelated third-party/vendor hostnames (e.g., `cdn.jsdelivr.net`, `fonts.googleapis.com`, `analytics.google.com`).

For each relevant hostname found:
```python
probely_create_extra_host(targetId, hostname="api.example.com", ip_address="")
```

**Always report** what was detected: "Detected API calls to `api.example.com`. Added as extra host."

If both layers returned zero extra hosts, report: "No external API hosts detected (checked via network requests and JS introspection)."