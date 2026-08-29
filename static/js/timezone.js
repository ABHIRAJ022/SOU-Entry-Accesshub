document.addEventListener('DOMContentLoaded', () => {
  try {
    let formatter;
    try {
      // Preferred modern options; some environments may not support dateStyle/timeStyle
      formatter = new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
        timeZoneName: 'short',
      });
    } catch (err) {
      // Fallback for environments that don't support dateStyle/timeStyle
      try {
        formatter = new Intl.DateTimeFormat(undefined, {
          year: 'numeric', month: 'short', day: 'numeric',
          hour: 'numeric', minute: '2-digit',
        });
      } catch (err2) {
        // As a last resort, use the default formatter
        formatter = Intl.DateTimeFormat();
      }
    }

    const resolvedTZ = (() => {
      try { return Intl.DateTimeFormat().resolvedOptions().timeZone; } catch (e) { return ''; }
    })();

    document.querySelectorAll('[data-local-time]').forEach((element) => {
      const timestamp = Date.parse(element.dataset.localTime || '');
      if (Number.isNaN(timestamp)) return;
      try { element.textContent = formatter.format(new Date(timestamp)); } catch (e) { element.textContent = new Date(timestamp).toString(); }
      if (resolvedTZ) element.title = `Device time (${resolvedTZ})`;
    });

    const legacyTimestamp = /([A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2} [AP]M)(?: IST)?/g;
    const compactTimestamp = /(\d{4}-\d{2}-\d{2} \d{2}:\d{2})(?: IST)?/g;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);
    textNodes.forEach((node) => {
      if (node.parentElement?.closest('[data-local-time]')) return;
      const original = node.nodeValue;
      let localized = original.replace(legacyTimestamp, (value, timestamp) => {
        const parsed = Date.parse(`${timestamp} GMT+0530`);
        return Number.isNaN(parsed) ? value : (() => { try { return formatter.format(new Date(parsed)); } catch (e) { return new Date(parsed).toString(); } })();
      });
      localized = localized.replace(compactTimestamp, (value, timestamp) => {
        const parsed = Date.parse(`${timestamp.replace(' ', 'T')}:00+05:30`);
        return Number.isNaN(parsed) ? value : (() => { try { return formatter.format(new Date(parsed)); } catch (e) { return new Date(parsed).toString(); } })();
      });
      if (localized !== original) node.nodeValue = localized;
    });
  } catch (e) {
    // Ensure any error here does not stop other scripts (e.g., dashboard.js)
    try { console.warn('timezone.js error:', e); } catch (_) {}
  }
});
