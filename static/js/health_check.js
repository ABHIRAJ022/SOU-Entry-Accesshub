(() => {
  const badge = document.querySelector('[data-health-badge]');
  async function checkHealth() {
    try {
      const response = await fetch('/api/health/', {headers: {'Accept': 'application/json'}, cache: 'no-store'});
      const data = await response.json();
      const operational = response.ok && data.status === 'operational';
      if (badge) { badge.textContent = operational ? 'System Health: Operational' : 'System Health: Degraded'; badge.className = `badge ${operational ? 'text-bg-success' : 'text-bg-warning'}`; }
    } catch (error) {
      if (badge) { badge.textContent = 'System Health: Offline'; badge.className = 'badge text-bg-danger'; }
    }
  }
  checkHealth(); setInterval(checkHealth, 60000);
})();
