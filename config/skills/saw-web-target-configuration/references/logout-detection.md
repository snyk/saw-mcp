# Configuring Logout Detection

**Always configure logout detection** after setting up authentication.

The login form selectors you recorded may also exist on the post-login page (e.g., a read-only username field on a profile section, or a password field inside a "change password" form). If you don't account for this, the scanner will think it's always logged out and fail. 

## 1. Pick the `check_session_url`

- **Default**: Use the **FULL absolute URL** you land on immediately after login (e.g., `https://app.example.com/dashboard`). Record it via `window.location.href` during the login sequence.
- **If login selectors still exist on the post-login landing page**: Pick a **different authenticated URL** where those selectors do NOT exist — for example a `/settings`, `/profile`, or `/dashboard` page. Browse the post-login page during recording to find a suitable link.
- **ALWAYS use absolute URLs** (e.g., `https://app.example.com/settings`) — **NEVER relative paths** (e.g., `/settings`).

## 2. Pick the logout detector

The best logout detectors are CSS selectors from the login form. But they **must only exist when logged out**.

- **If the selector does NOT exist on the post-login page** (the common case): use it directly.
  ```python
  logout_detector_type="sel"
  logout_detector_value="input[name='username']"
  ```
- **If the selector DOES exist on the post-login page**: use a **more specific CSS selector** that includes a parent element unique to the login form. For example, if the login form has `id="formlogin"`:
  ```python
  logout_detector_type="sel"
  logout_detector_value="#formlogin input[name='username']"
  ```
  Or scope via the form's action, a wrapping div, etc. The goal is a selector that **only matches the login form**, not the logged-in profile/settings page.

- **`logout_condition` parameter** — controls how multiple detectors combine:
  - `"any"` (default, OR): logged out if **ANY** detector matches. Use when each detector uniquely identifies the logged-out state.
  - `"all"` (AND): logged out only if **ALL** detectors match. Use as a **fallback** when you cannot craft a selector specific enough to avoid the post-login page. Add a second unambiguous detector (e.g., text that only appears on the login page) and set `logout_condition="all"` so both must match.

## 3. Configure via the MCP tool

**CRITICAL: You MUST explicitly provide both `logout_detector_type` and `logout_detector_value`. Do NOT rely on automatic detection.**

```python
probely_configure_logout_detection(
  targetId,
  enabled=True,
  check_session_url="https://app.example.com/dashboard",  # FULL absolute URL
  logout_detector_type="sel",    # REQUIRED
  logout_detector_value="#uid",  # REQUIRED — must NOT match when logged in
  logout_condition="any"         # "any" (default) or "all"
)
```

**Important**: Always use the **FULL URL** including protocol and domain (e.g., `https://app.example.com/dashboard`), NOT relative paths (e.g., `/dashboard`).