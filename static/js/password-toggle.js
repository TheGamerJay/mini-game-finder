/**
 * Password visibility toggle functionality for auth forms.
 * CSP-compliant external script with event listeners (no onclick handlers).
 */

function togglePassword(field, btn) {
  console.log('togglePassword called with field:', field.id, 'current type:', field.type);

  const showText = btn.querySelector('.show-text');
  const hideText = btn.querySelector('.hide-text');
  const isCurrentlyPassword = field.type === 'password';

  console.log('Elements found - showText:', !!showText, 'hideText:', !!hideText);
  console.log('Currently showing password:', !isCurrentlyPassword);

  // Toggle the field type
  field.type = isCurrentlyPassword ? 'text' : 'password';

  // Toggle visibility of emoji spans
  if (showText && hideText) {
    showText.style.display = isCurrentlyPassword ? 'none' : 'inline';
    hideText.style.display = isCurrentlyPassword ? 'inline' : 'none';
  }

  // Update ARIA attributes
  btn.setAttribute('aria-pressed', isCurrentlyPassword.toString());
  btn.setAttribute('aria-label', isCurrentlyPassword ? 'Hide password' : 'Show password');

  console.log('Toggled to type:', field.type);
}

// Initialize event listeners when DOM is ready
function initPasswordToggles() {
  console.log('Initializing password toggles...');
  const toggleButtons = document.querySelectorAll('.password-toggle');
  console.log('Found password toggle buttons:', toggleButtons.length);

  toggleButtons.forEach(function(btn, index) {
    console.log('Processing button', index + 1);

    // Find the password field in the same .password-field container
    const passwordFieldContainer = btn.closest('.password-field');
    const passwordField = passwordFieldContainer ? passwordFieldContainer.querySelector('input[type="password"], input[type="text"]') : null;

    console.log('Password field container found:', !!passwordFieldContainer);
    console.log('Password field found:', passwordField ? passwordField.id : 'none');

    if (passwordField) {
      console.log('Adding click listener to button for field:', passwordField.id);

      btn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('Password toggle clicked for field:', passwordField.id);
        togglePassword(passwordField, btn);
      });

      // Also add keyboard support
      btn.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          e.stopPropagation();
          console.log('Password toggle activated via keyboard for field:', passwordField.id);
          togglePassword(passwordField, btn);
        }
      });
    } else {
      console.warn('No password field found for toggle button', index + 1);
    }
  });

  console.log('Password toggle initialization complete');
}

// Initialize when DOM is ready
console.log('Password toggle script loaded, DOM state:', document.readyState);

if (document.readyState === 'loading') {
  console.log('DOM still loading, adding event listener');
  document.addEventListener('DOMContentLoaded', initPasswordToggles);
} else {
  console.log('DOM already ready, initializing immediately');
  initPasswordToggles();
}

// Also try after a short delay in case of timing issues
setTimeout(function() {
  console.log('Fallback initialization after 500ms');
  initPasswordToggles();
}, 500);