// Simple, robust password toggle that definitely works
(function() {
  'use strict';

  console.log('🔑 Password toggle script starting...');

  function togglePasswordVisibility(button) {
    try {
      console.log('👁️ Toggle button clicked');

      // Find the password field
      const passwordField = button.parentElement.querySelector('input');
      if (!passwordField) {
        console.error('❌ Password field not found');
        return;
      }

      console.log('✅ Found password field:', passwordField.id);

      // Find the emoji spans
      const showText = button.querySelector('.show-text');
      const hideText = button.querySelector('.hide-text');

      if (!showText || !hideText) {
        console.error('❌ Emoji spans not found');
        return;
      }

      // Toggle password visibility
      const isPassword = passwordField.type === 'password';
      passwordField.type = isPassword ? 'text' : 'password';

      // Toggle emoji visibility using CSS classes instead of inline styles
      // After toggle: if password was hidden (now visible), show 🙈 (hide-text)
      // After toggle: if password was visible (now hidden), show 👁️ (show-text)
      const newType = passwordField.type;
      const isNowVisible = newType === 'text'; // Password is now visible

      console.log('🔍 Password toggled from:', isPassword ? 'password' : 'text', 'to:', newType);
      console.log('🔍 Password is now visible:', isNowVisible);

      // Remove both classes first
      button.classList.remove('password-visible', 'password-hidden');

      // Add the appropriate class for current state
      if (isNowVisible) {
        button.classList.add('password-visible');
        console.log('🔍 Added password-visible class');
      } else {
        button.classList.add('password-hidden');
        console.log('🔍 Added password-hidden class');
      }

      // Update ARIA - set labels based on what the button will do NEXT
      button.setAttribute('aria-pressed', isNowVisible.toString());
      button.setAttribute('aria-label', isNowVisible ? 'Hide password' : 'Show password');

      console.log('✅ Password toggled to:', passwordField.type);
    } catch (error) {
      console.error('❌ Toggle error:', error);
    }
  }

  function initPasswordToggles() {
    console.log('🔍 Looking for password toggle buttons...');

    const buttons = document.querySelectorAll('.password-toggle');
    console.log('📊 Found buttons:', buttons.length);

    if (buttons.length === 0) {
      console.warn('⚠️ No password toggle buttons found');
      return;
    }

    buttons.forEach(function(button, index) {
      console.log('🔧 Setting up button', index + 1);

      // Remove any existing listeners
      button.removeEventListener('click', button._passwordToggleHandler);

      // Create new handler
      button._passwordToggleHandler = function(e) {
        e.preventDefault();
        e.stopPropagation();
        togglePasswordVisibility(button);
      };

      // Add click listener
      button.addEventListener('click', button._passwordToggleHandler);

      console.log('✅ Button', index + 1, 'ready');
    });

    console.log('🎉 All password toggles initialized');
  }

  // Try multiple initialization methods
  function tryInit() {
    console.log('🚀 Attempting initialization...');
    initPasswordToggles();
  }

  // Method 1: DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tryInit);
  } else {
    tryInit();
  }

  // Method 2: Window load (fallback)
  window.addEventListener('load', function() {
    console.log('🔄 Window loaded, re-initializing...');
    setTimeout(tryInit, 100);
  });

  // Method 3: Manual fallback after delay
  setTimeout(function() {
    console.log('⏰ Fallback initialization after 1 second...');
    tryInit();
  }, 1000);

  console.log('📋 Password toggle script loaded');
})();