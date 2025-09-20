// static/js/auth-check.js
// TEMP SAFE MODE: disable all login/logout interception that might override server logic
// Authentication-aware UI + optional session timeout + guarded logout

(function () {
  const SELECTOR_AUTH_ONLY = '.auth-only';

  function revealAuthUI(isAuth) {
    document.querySelectorAll(SELECTOR_AUTH_ONLY).forEach(el => {
      // Use inline style with !important to override CSS specificity
      if (isAuth) {
        // Show the element with appropriate display type
        if (el.classList.contains('btn')) {
          el.style.setProperty('display', 'inline-flex', 'important');
        } else {
          el.style.setProperty('display', 'block', 'important');
        }
      } else {
        el.style.setProperty('display', 'none', 'important');
      }
    });
  }

  async function fetchWhoAmI() {
    try {
      const r = await fetch('/__diag/whoami', { credentials: 'include' });
      const data = await r.json().catch(() => ({}));
      return data?.authenticated === true;
    } catch {
      return false; // fail safe: treat as not authenticated
    }
  }

  // Note: Session timeout is now handled by the main session monitoring system in base.html
  // This removes the old redundant idle timeout code to prevent conflicts

  // guardedLogout function removed - using pure server-side logout only

  function bindLogoutLinks() {
    // SAFE MODE: No guardedLogout, no auto-redirects. Let the server do its job.
    return;
  }

  async function initAuthUI() {
    // Fast path: trust server-provided data-authenticated to avoid FOUC
    const body = document.body;
    const hinted = body?.dataset?.authenticated;

    console.log('Auth check: data-authenticated =', hinted);

    if (hinted === 'true') {
      console.log('Auth check: Revealing UI based on server hint');
      revealAuthUI(true);
    }

    // Verify with backend (not strictly necessary on pages after login)
    const isAuth = await fetchWhoAmI();
    console.log('Auth check: Backend verification =', isAuth);
    revealAuthUI(isAuth);

    // Logout interception (only if using /api/clear-session guard)
    bindLogoutLinks();
  }

  document.addEventListener('DOMContentLoaded', initAuthUI);
})();