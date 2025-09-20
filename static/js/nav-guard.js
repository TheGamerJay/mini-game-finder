// Guarded Navigation (Prevent Duplicate Actions)
// Stop rapid clicks from causing double loads

(function() {
  'use strict';

  let navigating = false;
  let pendingActions = new Set();

  async function guarded(fn, key = null) {
    const actionKey = key || fn.toString();

    if (navigating || pendingActions.has(actionKey)) {
      return Promise.resolve(null);
    }

    navigating = true;
    pendingActions.add(actionKey);

    try {
      const result = await fn();
      return result;
    } finally {
      navigating = false;
      pendingActions.delete(actionKey);
    }
  }

  function guardedClick(handler, options = {}) {
    const { key = null, timeout = 5000, onDuplicate = null } = options;

    return async function guardedHandler(event, ...args) {
      const actionKey = key || handler.toString();

      if (pendingActions.has(actionKey)) {
        if (onDuplicate) {
          onDuplicate(event, ...args);
        }
        return;
      }

      pendingActions.add(actionKey);

      let timeoutId;
      if (timeout > 0) {
        timeoutId = setTimeout(() => {
          pendingActions.delete(actionKey);
        }, timeout);
      }

      try {
        await handler(event, ...args);
      } finally {
        if (timeoutId) clearTimeout(timeoutId);
        pendingActions.delete(actionKey);
      }
    };
  }

  function guardedSubmit(handler, options = {}) {
    const { key = null, timeout = 10000, disableForm = true } = options;

    return async function guardedSubmitHandler(event, form, data, ...args) {
      const actionKey = key || form.action || handler.toString();

      if (pendingActions.has(actionKey)) {
        event.preventDefault();
        return;
      }

      pendingActions.add(actionKey);

      let formElements = [];
      if (disableForm && form) {
        formElements = [...form.querySelectorAll('button, input[type="submit"]')];
        formElements.forEach(el => el.disabled = true);
        form.classList.add('form-submitting');
      }

      let timeoutId;
      if (timeout > 0) {
        timeoutId = setTimeout(() => {
          pendingActions.delete(actionKey);
          if (disableForm && form) {
            formElements.forEach(el => el.disabled = false);
            form.classList.remove('form-submitting');
          }
        }, timeout);
      }

      try {
        await handler(event, form, data, ...args);
      } finally {
        if (timeoutId) clearTimeout(timeoutId);
        pendingActions.delete(actionKey);

        if (disableForm && form) {
          formElements.forEach(el => el.disabled = false);
          form.classList.remove('form-submitting');
        }
      }
    };
  }

  function createNavigationGuard() {
    const guards = new Map();
    const activeGuards = new Set();

    return {
      guard: async (key, fn) => {
        if (activeGuards.has(key)) {
          return Promise.resolve(null);
        }

        activeGuards.add(key);

        try {
          const result = await fn();
          return result;
        } finally {
          activeGuards.delete(key);
        }
      },

      isActive: (key) => activeGuards.has(key),

      clear: (key) => {
        if (key) {
          activeGuards.delete(key);
        } else {
          activeGuards.clear();
        }
      },

      addGlobalGuard: (guardFn) => {
        const id = Math.random().toString(36).substr(2, 9);
        guards.set(id, guardFn);

        return () => guards.delete(id);
      },

      checkGlobalGuards: async () => {
        for (const [id, guardFn] of guards.entries()) {
          const canProceed = await guardFn();
          if (!canProceed) {
            return false;
          }
        }
        return true;
      }
    };
  }

  function preventDoubleClick(element, handler, options = {}) {
    const { delay = 300, onDuplicate = null } = options;
    let lastClickTime = 0;

    const wrappedHandler = (event) => {
      const now = Date.now();
      const timeSinceLastClick = now - lastClickTime;

      if (timeSinceLastClick < delay) {
        event.preventDefault();
        event.stopPropagation();
        if (onDuplicate) {
          onDuplicate(event);
        }
        return;
      }

      lastClickTime = now;
      handler(event);
    };

    element.addEventListener('click', wrappedHandler);

    return () => element.removeEventListener('click', wrappedHandler);
  }

  function throttleAction(fn, delay) {
    let lastExecution = 0;
    let timeoutId;

    return function throttledAction(...args) {
      const now = Date.now();
      const timeSinceLastExecution = now - lastExecution;

      if (timeSinceLastExecution >= delay) {
        lastExecution = now;
        return fn.apply(this, args);
      }

      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        lastExecution = Date.now();
        fn.apply(this, args);
      }, delay - timeSinceLastExecution);
    };
  }

  function createActionManager() {
    const actions = new Map();

    return {
      register: (key, handler, options = {}) => {
        const { guard = true, throttle = 0 } = options;

        let finalHandler = handler;

        if (throttle > 0) {
          finalHandler = throttleAction(finalHandler, throttle);
        }

        if (guard) {
          finalHandler = guardedClick(finalHandler, { key });
        }

        actions.set(key, finalHandler);
        return () => actions.delete(key);
      },

      execute: async (key, ...args) => {
        const handler = actions.get(key);
        if (!handler) {
          throw new Error(`Action "${key}" not found`);
        }

        return handler(...args);
      },

      clear: () => actions.clear(),

      list: () => [...actions.keys()]
    };
  }

  // Expose utilities
  window.NavGuard = {
    guarded,
    guardedClick,
    guardedSubmit,
    createNavigationGuard,
    preventDoubleClick,
    throttleAction,
    createActionManager,
    isNavigating: () => navigating,
    getPendingActions: () => [...pendingActions]
  };

})();