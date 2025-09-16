// auth-isolation.js - CSP-compliant auth page isolation
(function () {
  'use strict';

  function initAuthIsolation() {
    try {
      // Remove any SPA/hero overlays that might interfere with auth pages
      var killSelectors = '#app, #root, .spa-root, .hero, .hero-artwork, .login-hero';
      var killElements = document.querySelectorAll(killSelectors);
      killElements.forEach(function (element) {
        if (element && element.parentNode) {
          element.parentNode.removeChild(element);
        }
      });

      // Find auth root container (login-root, auth-root, or any *-root)
      var authRoot = document.getElementById('login-root') ||
                     document.getElementById('auth-root') ||
                     document.querySelector('[id$="-root"]');

      if (authRoot) {
        // Hide all other direct children of body except the auth root
        var bodyChildren = Array.prototype.slice.call(document.body.children);
        bodyChildren.forEach(function (element) {
          if (element !== authRoot &&
              !element.matches('.alert') &&
              !element.matches('.success') &&
              !element.matches('.csp-reporter') &&
              !element.matches('script')) {
            element.style.display = 'none';
          }
        });

        // Set background colors for full isolation
        document.documentElement.style.background = '#0b0b11';
        document.body.style.background = '#0b0b11';
        document.body.style.margin = '0';
        document.body.style.padding = '0';
      }
    } catch (e) {
      // Fail silently to avoid breaking the page
      console.debug('Auth isolation error:', e);
    }
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuthIsolation);
  } else {
    initAuthIsolation();
  }

  // Also run after a short delay to catch any late-loaded elements
  setTimeout(initAuthIsolation, 100);
})();