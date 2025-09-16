/**
 * Password visibility toggle functionality for auth forms.
 * CSP-compliant external script with event listeners (no onclick handlers).
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

// Initialize event listeners when DOM is ready
function initPasswordToggles() {
  const toggleButtons = document.querySelectorAll('.password-toggle');
  console.log('Found password toggle buttons:', toggleButtons.length);

  toggleButtons.forEach(function(btn) {
    // Find the associated password field (previous sibling input)
    const passwordField = btn.parentElement.querySelector('input[type="password"], input[type="text"]');
    console.log('Password field found:', passwordField ? passwordField.id : 'none');

    if (passwordField) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        console.log('Password toggle clicked for field:', passwordField.id);
        togglePassword(passwordField.id, btn);
      });
    }
  });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPasswordToggles);
} else {
  initPasswordToggles();
}