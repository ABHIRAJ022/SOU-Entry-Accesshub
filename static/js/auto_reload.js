document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('[data-auto-reload-toggle]');
  const AUTO_KEY = 'smartcampus_auto_reload';
  const RELOAD_INTERVAL_MS = 5000; // 5 seconds
  const isDashboardPath = () => location.pathname.startsWith('/dashboard');

  if (!toggle) return;

  // Read persisted preference (default: true)
  const persisted = localStorage.getItem(AUTO_KEY);
  let enabled = persisted === null ? true : persisted === 'true';

  const renderState = () => {
    toggle.textContent = enabled ? 'Auto-reload: ON' : 'Auto-reload: OFF';
    toggle.setAttribute('aria-pressed', enabled ? 'true' : 'false');
    toggle.classList.toggle('btn-primary', enabled);
    toggle.classList.toggle('btn-outline-secondary', !enabled);
  };

  let intervalId = null;

  const start = () => {
    stop();
    if (!enabled) return;
    if (!isDashboardPath()) return;
    // Use fetch-first to warm cache / validate page then reload to show any changes.
    intervalId = setInterval(() => {
      // Do a GET to ensure the server is reachable and the page has updates.
      fetch(window.location.href, { method: 'GET', cache: 'no-store', credentials: 'same-origin', headers: { 'Accept': 'text/html' } })
        .then(() => { window.location.reload(); })
        .catch(() => { /* ignore network errors and try again next tick */ });
    }, RELOAD_INTERVAL_MS);
  };

  const stop = () => {
    if (intervalId) { clearInterval(intervalId); intervalId = null; }
  };

  toggle.addEventListener('click', () => {
    enabled = !enabled;
    localStorage.setItem(AUTO_KEY, enabled ? 'true' : 'false');
    renderState();
    if (enabled) start(); else stop();
  });

  // Initialize UI and start if appropriate
  renderState();
  if (enabled) start();

  // If navigating within a single-page-like flow, ensure reload starts/stops on path changes
  window.addEventListener('popstate', () => {
    stop();
    if (enabled) start();
  });
});
