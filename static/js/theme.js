(() => {
  const root = document.documentElement;
  const toggle = document.querySelector('[data-theme-toggle]');
  const storedTheme = localStorage.getItem('campus-theme');
  if (storedTheme) root.dataset.bsTheme = storedTheme;

  const updateToggle = () => {
    if (!toggle) return;
    const dark = root.dataset.bsTheme === 'dark';
    toggle.setAttribute('aria-pressed', String(dark));
    toggle.innerHTML = dark ? '<span aria-hidden="true">☼</span><span>Light mode</span>' : '<span aria-hidden="true">☾</span><span>Dark mode</span>';
  };

  toggle?.addEventListener('click', () => {
    root.dataset.bsTheme = root.dataset.bsTheme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('campus-theme', root.dataset.bsTheme);
    updateToggle();
  });
  updateToggle();
})();
