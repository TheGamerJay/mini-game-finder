// static/js/auth-check.js
// Authentication-aware UI + optional session timeout + guarded logout

(function () {
  const SELECTOR_AUTH_ONLY = '.auth-only';

  function revealAuthUI(isAuth) {
    document.querySelectorAll(SELECTOR_AUTH_ONLY).forEach(el => {
      // Use inline style to avoid relying on class names here
      el.style.display = isAuth ? 'inline-flex' : 'none';
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

  // Optional: client-side idle timeout (disabled by default)
  const ENABLE_IDLE_TIMEOUT = false;              // set to true if you want it
  const TIMEOUT_DURATION_MS = 30 * 60 * 1000;     // 30 minutes
  const WARNING_AT_MS      = 25 * 60 * 1000;      // warn at 25 minutes
  let sessionTimeout, warningTimeout;

  function clearIdleTimers() {
    clearTimeout(sessionTimeout);
    clearTimeout(warningTimeout);
  }

  function startIdleTimers() {
    if (!ENABLE_IDLE_TIMEOUT) return;
    clearIdleTimers();

    warningTimeout = setTimeout(() => {
      // Non-blocking lightweight notice; avoid alert/confirm under CSP
      console.debug('Session idle: 5 minutes remaining');
    }, WARNING_AT_MS);

    sessionTimeout = setTimeout(() => {
      // Redirect to /logout which should invalidate server session
      window.location.href = '/logout';
    }, TIMEOUT_DURATION_MS);
  }

  function bindIdleResetters() {
    if (!ENABLE_IDLE_TIMEOUT) return;
    ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'].forEach(evt => {
      document.addEventListener(evt, startIdleTimers, { passive: true, capture: true });
    });
  }

  async function guardedLogout(e) {
    // Optional: Only intercept if you use an API-based logout.
    // If /logout is a server route that clears session, this can be skipped.
    e?.preventDefault?.();
    try {
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
      const headers = {
        'Content-Type': 'application/json',
        'X-Logout-Intent': 'yes'
      };
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }

      await fetch('/api/clear-session', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({ intent: 'logout', confirm: true })
      });
    } catch {
      // swallow – we'll still navigate to server logout
    } finally {
      window.location.href = '/logout';
    }
  }

  function bindLogoutLinks() {
    document.querySelectorAll('a[href="/logout"]').forEach(a => {
      // If you want to keep pure server-side logout, comment this out.
      a.addEventListener('click', guardedLogout, { once: true });
    });
  }

  async function initAuthUI() {
    // Fast path: trust server-provided data-authenticated to avoid FOUC
    const body = document.body;
    const hinted = body?.dataset?.authenticated;
    if (hinted === 'true') {
      revealAuthUI(true);
    }

    // Verify with backend (not strictly necessary on pages after login)
    const isAuth = await fetchWhoAmI();
    revealAuthUI(isAuth);

    // Idle timer wiring (optional)
    bindIdleResetters();
    startIdleTimers();

    // Logout interception (only if using /api/clear-session guard)
    bindLogoutLinks();
  }

  document.addEventListener('DOMContentLoaded', initAuthUI);
})();