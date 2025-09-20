// Abortable Listeners & Fetch (Automatic Cleanup)
// Eliminate "dangling" listeners and ongoing fetches on page switches

(function() {
  'use strict';

  function withAbort(setup) {
    const ctrl = new AbortController();
    const cleanup = setup(ctrl.signal);
    return () => {
      ctrl.abort();
      if (cleanup && typeof cleanup === 'function') {
        cleanup();
      }
    };
  }

  function createLifecycle() {
    const controllers = new Set();
    const cleanupFns = new Set();

    const lifecycle = {
      addAbortable(setup) {
        const ctrl = new AbortController();
        controllers.add(ctrl);

        const cleanup = setup(ctrl.signal);
        if (cleanup && typeof cleanup === 'function') {
          cleanupFns.add(cleanup);
        }

        return () => {
          ctrl.abort();
          controllers.delete(ctrl);
          if (cleanup) {
            cleanup();
            cleanupFns.delete(cleanup);
          }
        };
      },

      addCleanup(fn) {
        cleanupFns.add(fn);
        return () => cleanupFns.delete(fn);
      },

      destroy() {
        controllers.forEach(ctrl => ctrl.abort());
        cleanupFns.forEach(fn => {
          try {
            fn();
          } catch (e) {
            console.error('Lifecycle cleanup error:', e);
          }
        });
        controllers.clear();
        cleanupFns.clear();
      }
    };

    return lifecycle;
  }

  function withTimeout(promise, ms, message = 'Operation timed out') {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(message)), ms);
      promise
        .then(resolve, reject)
        .finally(() => clearTimeout(timer));
    });
  }

  function abortableFetch(url, options = {}) {
    const controller = new AbortController();
    const signal = options.signal
      ? AbortSignal.any([options.signal, controller.signal])
      : controller.signal;

    const fetchPromise = fetch(url, { ...options, signal });

    return {
      promise: fetchPromise,
      abort: () => controller.abort(),
      signal: controller.signal
    };
  }

  function createAbortGroup() {
    const controllers = new Set();

    return {
      signal() {
        const ctrl = new AbortController();
        controllers.add(ctrl);
        return ctrl.signal;
      },

      abort() {
        controllers.forEach(ctrl => ctrl.abort());
        controllers.clear();
      }
    };
  }

  // Expose utilities
  window.Lifecycles = {
    withAbort,
    createLifecycle,
    withTimeout,
    abortableFetch,
    createAbortGroup
  };

})();