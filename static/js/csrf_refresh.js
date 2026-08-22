(() => {
  const sameOrigin = (url) => new URL(url, window.location.href).origin === window.location.origin;
  const refreshToken = async (form) => {
    const action = form.getAttribute('action') || window.location.href;
    if (!sameOrigin(action)) return null;
    const response = await fetch(action, {credentials: 'same-origin', headers: {'X-CSRF-Refresh': '1'}, cache: 'no-store'});
    if (!response.ok) return null;
    const html = await response.text();
    const documentFragment = new DOMParser().parseFromString(html, 'text/html');
    return documentFragment.querySelector('input[name="csrfmiddlewaretoken"]')?.value || null;
  };

  document.addEventListener('submit', async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || form.dataset.csrfRefreshing === '1' || form.dataset.csrfRefresh === 'false' || form.method.toLowerCase() !== 'post') return;
    event.preventDefault();
    form.dataset.csrfRefreshing = '1';
    const submit = form.querySelector('[type="submit"]');
    if (submit) submit.disabled = true;
    try {
      const token = await refreshToken(form);
      const field = form.querySelector('input[name="csrfmiddlewaretoken"]');
      if (!token || !field) { HTMLFormElement.prototype.submit.call(form); return; }
      field.value = token;
      HTMLFormElement.prototype.submit.call(form);
    } catch (error) {
      form.dataset.csrfRefreshing = '0';
      if (submit) submit.disabled = false;
      form.submit();
    }
  });
})();
