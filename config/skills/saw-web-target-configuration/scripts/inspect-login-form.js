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

  // ── Canvas-rendered login detection (e.g. Flutter web, game engines, custom widgets) ──
  // Canvas-rendered logins paint the fields & button on a <canvas>; there is no
  // clickable DOM button. Report canvas surfaces so the caller knows to use
  // bclick/bfill_value with coordinates (see references/sequence-format.md).
  const canvasSelector = (c) => {
    if (isStable(c.id)) return `#${c.id}`;
    if (typeof c.className === 'string' && c.className.trim()) {
      return 'canvas.' + c.className.trim().split(/\s+/).join('.');
    }
    return 'canvas';
  };
  const canvases = Array.from(document.querySelectorAll('canvas'))
    .filter((c) => c.offsetParent !== null || (c.width > 0 && c.height > 0))
    .map((c) => {
      const r = c.getBoundingClientRect();
      return {
        selector: canvasSelector(c),
        // bclick coords are canvas-relative; width/height come from the rect
        width: Math.round(r.width || c.width),
        height: Math.round(r.height || c.height),
      };
    });
  const canvasNote =
    'Canvas surface detected: the login UI may be painted on a <canvas> with no DOM ' +
    'submit button. Read the page <script> or screenshot to find field/button ' +
    'rectangles, then use bclick (with coords {x,y,width,height} relative to the ' +
    'canvas) to focus fields and submit. Use fill_value on any hidden <input> that ' +
    'receives keystrokes, or bfill_value on the canvas otherwise. ' +
    'See references/sequence-format.md (Canvas-Rendered Logins).';

  // ── Shadow DOM login detection ──
  // Custom elements often place the real <input> inside an OPEN shadowRoot, so
  // document.querySelector cannot see them. The Snyk recorder targets the INNER
  // element with a simple selector (e.g. input[type="password"]) and marks the
  // step with xpath "/html/node/shadow". Do NOT use `host input` piercing
  // selectors or the host element's name — a shadow-piercing search resolves the
  // css within a single root and cannot cross the boundary.
  const deepInputs = [];
  const deepButtons = [];
  (function collectShadow(root) {
    for (const el of root.querySelectorAll('*')) {
      if (el.shadowRoot) {
        for (const inp of el.shadowRoot.querySelectorAll('input, textarea')) deepInputs.push(inp);
        for (const b of el.shadowRoot.querySelectorAll('button, input[type="submit"]')) deepButtons.push(b);
        collectShadow(el.shadowRoot);
      }
    }
  })(document);
  // Recorder-style selector for a shadow-DOM inner element (getCustomSelector
  // logic): inner element only — id if stable, else tag[type][name]. No form or
  // host prefix, because closest('form')/closest('body') do not cross the boundary.
  const shadowSelector = (el) => {
    const tag = el.tagName.toLowerCase();
    if (isStable(el.id)) return `${tag}#${el.id}`;
    let s = tag;
    if (el.getAttribute && el.getAttribute('type')) s += `[type="${el.getAttribute('type')}"]`;
    if (el.getAttribute && el.getAttribute('name')) s += `[name="${el.getAttribute('name')}"]`;
    return s;
  };
  // Attribute-based XPath for a shadow-DOM inner element. Probely's replayer can
  // evaluate a real XPath that pierces the shadow root (e.g.
  // //input[@name='user' and @autocomplete='username']), which is more robust than
  // the raw "/html/node/shadow" sentinel. Fall back to the sentinel only when the
  // element exposes no distinguishing attributes.
  const shadowXPath = (el) => {
    const tag = el.tagName.toLowerCase();
    const preds = [];
    for (const a of ['name', 'autocomplete', 'id', 'type', 'placeholder', 'aria-label']) {
      const v = el.getAttribute && el.getAttribute(a);
      if (v && !v.includes("'")) preds.push(`@${a}='${v}'`);
    }
    return preds.length ? `//${tag}[${preds.join(' and ')}]` : '/html/node/shadow';
  };
  // Count how many elements a selector matches across ALL shadow roots (the same
  // shadow-piercing search the replayer performs). Used to flag non-unique selectors:
  // different shadow roots are isolated scopes, so inner elements can share id/name/type.
  const deepCountCss = (sel) => {
    let n = 0;
    (function walk(root) {
      try { n += root.querySelectorAll(sel).length; } catch (ex) { /* invalid selector */ }
      for (const el of root.querySelectorAll('*')) if (el.shadowRoot) walk(el.shadowRoot);
    })(document);
    return n;
  };
  const describeShadow = (el) => {
    if (!el) return null;
    const selector = shadowSelector(el);
    const d = {
      tag: el.tagName, id: el.id, name: el.name, type: el.type,
      value: el.value,
      selector,
      xpath: shadowXPath(el)
    };
    const matches = deepCountCss(selector);
    if (matches > 1) {
      d.ambiguous = true;
      d.warning =
        'Selector "' + selector + '" matches ' + matches + ' elements across shadow ' +
        'roots — shadow roots are isolated scopes, so inner elements can share ' +
        'id/name/type. Refine it with a distinguishing attribute (autocomplete, ' +
        'placeholder, aria-label) or a positional XPath so it uniquely targets THIS ' +
        'field. See references/sequence-format.md (Shadow DOM Inputs).';
    }
    return d;
  };
  const shadowPassword = deepInputs.find((i) => i.type === 'password');
  const shadowNote =
    'Shadow DOM login detected: the real <input> elements live inside open shadow ' +
    'roots. For each fill_value, target the INNER element with the simple ' +
    '`selector` and the attribute-based `xpath` below (a real XPath that pierces ' +
    'the shadow root, e.g. //input[@type=\'password\']; the "/html/node/shadow" ' +
    'sentinel is only a fallback when no attributes exist). Do NOT use ' +
    '`host input` piercing selectors or the host element name. Shadow roots are ' +
    'isolated scopes, so inner elements can share id/name/type — make sure each ' +
    'selector/xpath is UNIQUE across all shadow roots (see `ambiguous`/`warning`). ' +
    'See references/sequence-format.md (Shadow DOM Inputs).';

  const passwordField = document.querySelector('input[type="password"]');

  // ── Shadow DOM login: password field lives inside an open shadow root ──
  if (!passwordField && shadowPassword) {
    const shadowUser =
      deepInputs.find((i) => i !== shadowPassword && (['text', 'email'].includes(i.type) || /user|email|login/i.test(i.name || i.id || ''))) ||
      deepInputs.find((i) => i !== shadowPassword);
    // Submit button: prefer a light-DOM button, fall back to a shadow-DOM one.
    const lightSubmit = document.querySelector('form button[type="submit"], button[type="submit"], input[type="submit"], button:not([type])');
    const shadowSubmit = deepButtons.find((b) => b.type === 'submit' || !b.type) || deepButtons[0];
    const submitEl = lightSubmit || shadowSubmit;
    return {
      step: 'shadow_dom',
      note: shadowNote,
      username: describeShadow(shadowUser),
      password: describeShadow(shadowPassword),
      submit: submitEl
        ? (submitEl.getRootNode() === document ? describeSubmit(submitEl) : describeShadow(submitEl))
        : null
    };
  }

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

    const out = {
      step: 'single_page',
      username: describe(usernameField),
      password: describe(passwordField),
      submit: describeSubmit(submitEl)
    };
    // No DOM submit button + a canvas present ⇒ likely a canvas-rendered login.
    if (!submitEl && canvases.length) {
      out.step = 'canvas';
      out.canvas = canvases;
      out.note = canvasNote;
    } else if (canvases.length) {
      out.canvas = canvases;
    }
    return out;
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

  // Pure canvas login: no password field and no usable DOM input, but a canvas exists.
  if (canvases.length && !primaryInput) {
    return {
      step: 'canvas',
      canvas: canvases,
      note: canvasNote,
      input: describe(primaryInput),
      button: describeSubmit(stepButton)
    };
  }

  // Shadow DOM step: no light-DOM input here, but a shadow-DOM input exists.
  if (!primaryInput && deepInputs.length) {
    const shadowInput = deepInputs.find((i) => ['text', 'email'].includes(i.type) || /user|email|login/i.test(i.name || i.id || '')) || deepInputs[0];
    const shadowSubmit = document.querySelector('button[type="submit"], input[type="submit"], button:not([type])') ||
      deepButtons.find((b) => b.type === 'submit' || !b.type) || deepButtons[0];
    return {
      step: 'shadow_dom',
      note: shadowNote,
      input: describeShadow(shadowInput),
      button: shadowSubmit
        ? (shadowSubmit.getRootNode() === document ? describeSubmit(shadowSubmit) : describeShadow(shadowSubmit))
        : null
    };
  }

  return {
    step: 'multi_step',
    note: 'No password field on this screen. Fill the input, click the button, then run this script again on the next screen.',
    input: describe(primaryInput),
    button: describeSubmit(stepButton),
    ...(canvases.length ? { canvas: canvases } : {}),
    ...(deepInputs.length ? { shadow: deepInputs.map(describeShadow) } : {})
  };
}
