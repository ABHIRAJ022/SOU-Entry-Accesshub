document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('[data-auto-reload-toggle]');
  const AUTO_KEY = 'smartcampus_auto_reload';
  const RELOAD_INTERVAL_MS = 30000; // Avoid repeatedly re-fetching database-backed dashboards.
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
    intervalId = setInterval(() => {
      window.location.reload();
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
