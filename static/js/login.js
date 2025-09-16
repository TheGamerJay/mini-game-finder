// Login page functionality
function togglePw(id, btn) {
  const i = document.getElementById(id);
  const show = i.type === 'password';
  i.type = show ? 'text' : 'password';
  btn.setAttribute('aria-pressed', show ? 'true' : 'false');
  btn.textContent = show ? '🙈' : '👁';
}