document.addEventListener('DOMContentLoaded', () => {
  const csrfToken = () => document.querySelector('[name=csrfmiddlewaretoken]')?.value;
  document.querySelectorAll('[data-approval]').forEach((button) => button.addEventListener('click', async () => {
    button.disabled = true;
    const response = await fetch(button.dataset.url, {method: 'POST', headers: {'X-CSRFToken': csrfToken(), 'Accept': 'application/json'}, body: new URLSearchParams({action: button.dataset.action})});
    if (response.ok) button.closest('[data-user-row]').remove();
    else if (response.status === 403) window.location.reload();
    else button.disabled = false;
  }));
  const search = document.querySelector('[data-student-search]'); const results = document.querySelector('[data-student-results]');
  if (search) search.addEventListener('input', async () => { const response = await fetch(`/dashboard/students/lookup/?q=${encodeURIComponent(search.value)}`); const data = await response.json(); results.innerHTML = data.results.map((student) => `<tr><td>${student.name}</td><td>${student.enrollment_number}</td><td>${student.email_verified ? 'Verified' : 'Unverified'}</td><td>${student.approved ? 'Approved' : 'Pending'}</td></tr>`).join(''); });
});
