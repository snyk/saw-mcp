() => {
  // Helpers
  const isStable = (id) => id && !/\d{3,}|[a-f0-9]{8,}/.test(id);
  const selectorFor = (el) => {
    if (!el) return null;
    if (el.name) return `${el.tagName.toLowerCase()}[name="${el.name}"]`;
    if (isStable(el.id)) return `#${el.id}`;
    if (el.type) return `${el.tagName.toLowerCase()}[type="${el.type}"]`;
    return null;
  };
  const describe = (el) => !el ? null : {
    tag: el.tagName, id: el.id, name: el.name, type: el.type,
    value: el.value, text: el.textContent?.trim()?.slice(0, 40),
    isStableId: isStable(el.id), selector: selectorFor(el)
  };
  const describeSubmit = (el) => {
    if (!el) return null;
    const d = describe(el);
    // For submit elements, prefer compound selectors when possible
    d.selector = el.name
      ? `${el.tagName.toLowerCase()}[type="${el.type || 'submit'}"][name="${el.name}"]`
      : d.selector;
    return d;
  };

  const passwordField = document.querySelector('input[type="password"]');

  // ── Single-page login: password field IS visible ──
  if (passwordField) {
    const form = passwordField.closest('form')
      || passwordField.closest('div, table, section, fieldset, main');

    let usernameField = null;
    if (form) {
      usernameField = form.querySelector(
        'input[type="text"], input[type="email"], input[name*="user"], input[name*="email"], input[name*="login"]'
      );
    }
    if (!usernameField) {
      const all = Array.from(document.querySelectorAll('input[type="text"], input[type="email"]'));
      usernameField = all.reverse().find(
        el => el.compareDocumentPosition(passwordField) & Node.DOCUMENT_POSITION_FOLLOWING
      );
    }

    let submitEl = null;
    if (form) {
      submitEl = form.querySelector('input[type="submit"], button[type="submit"], button:not([type])');
    }
    if (!submitEl) {
      const all = Array.from(document.querySelectorAll('input[type="submit"], button[type="submit"]'));
      submitEl = all.find(
        el => passwordField.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING
      ) || all[all.length - 1];
    }

    return {
      step: 'single_page',
      username: describe(usernameField),
      password: describe(passwordField),
      submit: describeSubmit(submitEl)
    };
  }

  // ── Multi-step login: no password field on this screen ──
  // Find the primary visible input (username/email) and the step's action button
  const candidates = Array.from(document.querySelectorAll(
    'input[type="text"], input[type="email"], input[name*="user"], input[name*="email"], input[name*="login"]'
  )).filter(el => el.offsetParent !== null); // visible only

  // Pick the most likely login input (prefer inputs inside a form, skip search boxes)
  let primaryInput = null;
  for (const el of candidates) {
    const inForm = el.closest('form');
    const looksLikeSearch = /search|query|q$/i.test(el.name || '') || /search|query|q$/i.test(el.id || '');
    if (!looksLikeSearch) { primaryInput = el; break; }
  }
  if (!primaryInput && candidates.length) primaryInput = candidates[0];

  const container = primaryInput
    ? (primaryInput.closest('form') || primaryInput.closest('div, table, section, fieldset, main'))
    : document.body;

  let stepButton = null;
  if (container) {
    stepButton = container.querySelector('input[type="submit"], button[type="submit"], button:not([type])');
  }
  if (!stepButton) {
    stepButton = document.querySelector('input[type="submit"], button[type="submit"]');
  }

  return {
    step: 'multi_step',
    note: 'No password field on this screen. Fill the input, click the button, then run this script again on the next screen.',
    input: describe(primaryInput),
    button: describeSubmit(stepButton)
  };
}
