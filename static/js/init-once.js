// One-Time, Mutation-Safe Initializers
// Prevent double-binding when DOM updates or partial rerenders happen

(function() {
  'use strict';

  function initOnce(root = document, selector, init) {
    root.querySelectorAll(selector).forEach(el => {
      if (el.dataset._inited) return;
      el.dataset._inited = "1";
      init(el);
    });
  }

  function initOnceWithCleanup(root = document, selector, init, cleanup) {
    root.querySelectorAll(selector).forEach(el => {
      if (el.dataset._inited) return;
      el.dataset._inited = "1";

      const teardown = init(el);

      if (cleanup || teardown) {
        const observer = new MutationObserver((mutations) => {
          mutations.forEach((mutation) => {
            mutation.removedNodes.forEach((node) => {
              if (node === el || (node.contains && node.contains(el))) {
                if (teardown) teardown();
                if (cleanup) cleanup(el);
                observer.disconnect();
              }
            });
          });
        });

        observer.observe(root, { childList: true, subtree: true });
      }
    });
  }

  function reinitOnMutation(root = document, selector, init, options = {}) {
    const { immediate = true, debounceMs = 0 } = options;

    if (immediate) {
      initOnce(root, selector, init);
    }

    let timeoutId;
    const observer = new MutationObserver(() => {
      if (debounceMs > 0) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => initOnce(root, selector, init), debounceMs);
      } else {
        initOnce(root, selector, init);
      }
    });

    observer.observe(root, {
      childList: true,
      subtree: true,
      ...options.observerOptions
    });

    return () => {
      observer.disconnect();
      if (timeoutId) clearTimeout(timeoutId);
    };
  }

  // Expose utilities
  window.InitOnce = {
    initOnce,
    initOnceWithCleanup,
    reinitOnMutation
  };

})();