(() => {
  const root = document.documentElement;
  const toggle = document.querySelector('[data-theme-toggle]');
  const storedTheme = localStorage.getItem('campus-theme');
  if (storedTheme) root.dataset.bsTheme = storedTheme;

  const updateToggle = () => {
    if (!toggle) return;
    const dark = root.dataset.bsTheme === 'dark';
    toggle.setAttribute('aria-pressed', String(dark));
    const icon = document.createElement('span');
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = dark ? '☼' : '☾';
    const label = document.createElement('span');
    label.textContent = dark ? 'Light mode' : 'Dark mode';
    toggle.replaceChildren(icon, label);
  };

  toggle?.addEventListener('click', () => {
    root.dataset.bsTheme = root.dataset.bsTheme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('campus-theme', root.dataset.bsTheme);
    updateToggle();
  });
  updateToggle();
})();
