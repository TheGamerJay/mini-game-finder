// Event Delegation Helper (with Optional Filter)
// Bind once to a stable parent; never chase dynamic children

(function() {
  'use strict';

  function delegate(parent, type, selector, handler, opts = {}) {
    const listener = (e) => {
      const target = e.target.closest(selector);
      if (target && parent.contains(target)) {
        handler(e, target);
      }
    };

    parent.addEventListener(type, listener, opts);

    return () => parent.removeEventListener(type, listener, opts);
  }

  function delegateMultiple(parent, eventMap, opts = {}) {
    const teardowns = [];

    Object.entries(eventMap).forEach(([eventType, handlers]) => {
      Object.entries(handlers).forEach(([selector, handler]) => {
        teardowns.push(delegate(parent, eventType, selector, handler, opts));
      });
    });

    return () => teardowns.forEach(fn => fn());
  }

  function delegateWithGuard(parent, type, selector, handler, guard, opts = {}) {
    return delegate(parent, type, selector, (e, target) => {
      if (guard(e, target)) {
        handler(e, target);
      }
    }, opts);
  }

  function delegateData(parent, type, dataAction, handler, opts = {}) {
    return delegate(parent, type, `[data-action="${dataAction}"]`, handler, opts);
  }

  function delegateForm(parent, handler, opts = {}) {
    return delegate(parent, 'submit', 'form', (e, form) => {
      e.preventDefault();
      const data = Object.fromEntries(new FormData(form));
      handler(e, form, data);
    }, opts);
  }

  // Expose utilities
  window.Delegate = {
    delegate,
    delegateMultiple,
    delegateWithGuard,
    delegateData,
    delegateForm
  };

})();