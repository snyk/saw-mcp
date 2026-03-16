# Login Sequence JSON Format

The sequence format (based on the [Snyk API&Web Sequence Recorder](https://github.com/Probely/sequence-recorder)):

**IMPORTANT: Use Custom Fields; Credentials Manager Is Optional**

**Always use custom field placeholders for username and password** instead of hardcoding them in the sequence. **Do not apply the credentials manager by default** — prompt the user to choose whether to use it for the password.

- Use `[CUSTOM_USERNAME]` placeholder for the username field — map to inline `value` in custom_field_mappings (not sensitive)
- Use `[CUSTOM_PASSWORD]` placeholder for the password field. **If the user opted in to credentials management**, create a credential via `probely_create_credential` and pass its `uri` (e.g. `credentials://xxxx`) as the `value` in custom_field_mappings. **If not**, the user may provide the password to use inline in custom_field_mappings.
- **2FA OTP codes should remain hardcoded** in the sequence (when the user opts in to credentials for 2FA, store the TOTP seed via credential manager in step 3)

Example sequence with custom fields:

```json
[
  {
    "type": "goto",
    "timestamp": 1234567890000,
    "url": "https://app.example.com/login",
    "windowWidth": 1280,
    "windowHeight": 720,
    "urlType": "force"
  },
  { 
    "type": "click",
    "timestamp": 1234567891000,
    "css": "input[name='email']",
    "xpath": "//*[@name='email']",
    "value": "",
    "frame": null
  },
  {
    "type": "fill_value",
    "timestamp": 1234567892000,
    "css": "input[name='email']",
    "xpath": "//*[@name='email']",
    "value": "[CUSTOM_USERNAME]",
    "frame": null
  },
  { 
    "type": "click",
    "timestamp": 1234567893000,
    "css": "input[name='password']",
    "xpath": "/html/body/form/input[2]",
    "value": "",
    "frame": null
  },
  {
    "type": "fill_value",
    "timestamp": 1234567894000,
    "css": "input[name='password']",
    "xpath": "/html/body/form/input[2]",
    "value": "[CUSTOM_PASSWORD]",
    "frame": null
  },
  {
    "type": "click",
    "timestamp": 1234567895000,
    "css": "button[name='btnSubmit']",
    "xpath": "/html/body/form/button",
    "value": "Sign In",
    "frame": null
  }
]
```

**For 2FA**, use the `otp_code` returned by `probely_configure_2fa_totp` **hardcoded** in the sequence (do NOT use a custom field for OTP):
```json
{
  "type": "fill_value",
  "timestamp": 1234567896000,
  "css": "#otp",
  "xpath": "//*[@id='otp']",
  "value": "829182",
  "frame": null
}
```
Probely will automatically convert `fill_value` entries matching the configured OTP code to `fill_otp` type at scan time.

## Sequence Event Types

| Type | Description | Fields |
|------|-------------|--------|
| `goto` | Navigate to URL | `url`, `windowWidth`, `windowHeight`, `urlType` |
| `click` | Click an element | `css`, `xpath`, `value` (button text), `frame` |
| `dblclick` | Double-click | Same as click |
| `fill_value` | Enter text in input/textarea | `css`, `xpath`, `value` (text to enter), `frame` |
| `fill_otp` | Enter OTP code (auto-converted) | `css`, `xpath`, `value` (OTP code), `frame` |
| `change` | Checkbox/radio/select change | `css`, `xpath`, `subtype`, `checked`/`selected`, `frame` |
| `press_key` | Press a key | `css`, `xpath`, `value` (keyCode), `frame` |
| `mouseover` | Hover over element | `css`, `xpath`, `value`, `frame` |