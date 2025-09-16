/**
 * Password visibility toggle functionality for auth forms.
 * CSP-compliant external script to avoid inline JavaScript.
 */

function togglePassword(fieldId, btn) {
  const field = document.getElementById(fieldId);
  const showText = btn.querySelector('.show-text');
  const hideText = btn.querySelector('.hide-text');
  const showing = field.type === 'text';

  field.type = showing ? 'password' : 'text';
  showText.style.display = showing ? 'inline' : 'none';
  hideText.style.display = showing ? 'none' : 'inline';
  btn.setAttribute('aria-pressed', (!showing).toString());
  btn.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
}

// Make function globally available for onclick handlers
window.togglePassword = togglePassword;