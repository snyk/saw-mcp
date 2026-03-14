() => {
  const found = new Set();
  const targetHost = location.hostname;

  const extractHosts = (str) => {
    const matches = str.match(/https?:\/\/[a-zA-Z0-9][-a-zA-Z0-9.]*[a-zA-Z0-9](?::\d+)?/g);
    if (matches) matches.forEach(u => {
      try {
        const h = new URL(u).hostname;
        if (h !== targetHost && h.endsWith(targetHost.replace(/^www\./, '').replace(/^[^.]+\./, '')))
          found.add(h);
      } catch {}
    });
  };

  // Next.js embedded data
  if (window.__NEXT_DATA__) extractHosts(JSON.stringify(window.__NEXT_DATA__));

  // Environment / config globals (common patterns)
  for (const key of Object.keys(window)) {
    if (/env|config|settings|api/i.test(key)) {
      try { extractHosts(JSON.stringify(window[key])); } catch {}
    }
  }

  // Inline and external script contents
  document.querySelectorAll('script:not([src])').forEach(s => extractHosts(s.textContent));

  // Meta tags (some apps store API URLs here)
  document.querySelectorAll('meta[content*="http"]').forEach(m => extractHosts(m.content));

  return { apiHosts: [...found], targetHost };
}