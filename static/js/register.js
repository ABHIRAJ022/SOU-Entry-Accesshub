document.addEventListener('DOMContentLoaded', () => {
  const role = document.querySelector('#id_role');
  const studentFields = document.querySelectorAll('[data-student-only-field]');
  if (!role) return;
  const update = () => {
    const isStudent = role.value === 'STUDENT';
    studentFields.forEach((field) => {
      field.classList.toggle('d-none', !isStudent);
      field.querySelector('input, select')?.toggleAttribute('required', isStudent && field.dataset.studentOnlyField === 'branch');
    });
  };
  role.addEventListener('change', update);
  update();
});