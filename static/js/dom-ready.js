// Universal DOM-Ready Harness - Professional grade DOM management
// Based on bulletproof patterns for predictable element access

(function() {
  'use strict';

  // Run a callback once the DOM is safe to touch (idempotent)
  function onDomReady(cb) {
    if (document.readyState === "interactive" || document.readyState === "complete") {
      queueMicrotask(cb); // run after any ongoing script microtasks
    } else {
      document.addEventListener("DOMContentLoaded", cb, { once: true });
    }
  }

  // Optional: guard against multiple inits (e.g., hot reload / re-entry)
  function createInitOnce() {
    let _initialized = false;
    return function initOnce(fn) {
      if (_initialized) return;
      _initialized = true;
      fn();
    };
  }

  // Wait for an element that might not exist yet (with timeout)
  function waitForEl(selector, { root = document, timeout = 5000 } = {}) {
    return new Promise((resolve, reject) => {
      const found = root.querySelector(selector);
      if (found) return resolve(found);

      const timer = timeout
        ? setTimeout(() => {
            observer.disconnect();
            reject(new Error(`waitForEl timeout: ${selector}`));
          }, timeout)
        : null;

      const observer = new MutationObserver(() => {
        const el = root.querySelector(selector);
        if (el) {
          if (timer) clearTimeout(timer);
          observer.disconnect();
          resolve(el);
        }
      });

      observer.observe(root, { childList: true, subtree: true });
    });
  }

  // Safe element getter with explicit error handling
  function getRequiredElement(id, context = 'Unknown') {
    const element = document.getElementById(id);
    if (!element) {
      console.error(`[DOM-READY] Missing required element: #${id} (Context: ${context})`);
      return null;
    }
    return element;
  }

  // Safe multiple element getter
  function getRequiredElements(ids, context = 'Unknown') {
    const elements = {};
    let allFound = true;

    for (const id of ids) {
      elements[id] = getRequiredElement(id, context);
      if (!elements[id]) {
        allFound = false;
      }
    }

    if (!allFound) {
      console.error(`[DOM-READY] Some required elements missing in context: ${context}`);
      return null;
    }

    return elements;
  }

  // Expose utilities globally
  window.DOMReady = {
    onDomReady,
    createInitOnce,
    waitForEl,
    getRequiredElement,
    getRequiredElements
  };

})();