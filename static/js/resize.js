// Resize-Safe Components (ResizeObserver)
// Handle container resizes without polling

(function() {
  'use strict';

  function onResize(el, handler, options = {}) {
    const { debounceMs = 0, includeInitial = true } = options;

    let timeoutId;
    const debouncedHandler = debounceMs > 0
      ? (entries) => {
          clearTimeout(timeoutId);
          timeoutId = setTimeout(() => handler(el, entries), debounceMs);
        }
      : () => handler(el);

    const ro = new ResizeObserver(debouncedHandler);
    ro.observe(el);

    if (includeInitial) {
      setTimeout(() => handler(el), 0);
    }

    return () => {
      ro.disconnect();
      if (timeoutId) clearTimeout(timeoutId);
    };
  }

  function onResizeMany(selector, handler, options = {}) {
    const elements = document.querySelectorAll(selector);
    const teardowns = [];

    elements.forEach(el => {
      const teardown = onResize(el, handler, options);
      teardowns.push(teardown);
    });

    return () => teardowns.forEach(fn => fn());
  }

  function createResizeManager() {
    const observers = new Map();

    return {
      observe(el, handler, options = {}) {
        if (observers.has(el)) {
          this.unobserve(el);
        }

        const teardown = onResize(el, handler, options);
        observers.set(el, teardown);

        return () => this.unobserve(el);
      },

      unobserve(el) {
        const teardown = observers.get(el);
        if (teardown) {
          teardown();
          observers.delete(el);
        }
      },

      observeMany(selector, handler, options = {}) {
        const elements = document.querySelectorAll(selector);
        const teardowns = [];

        elements.forEach(el => {
          const teardown = this.observe(el, handler, options);
          teardowns.push(teardown);
        });

        return () => teardowns.forEach(fn => fn());
      },

      clear() {
        observers.forEach(teardown => teardown());
        observers.clear();
      }
    };
  }

  function responsiveBreakpoints(el, breakpoints, handler, options = {}) {
    let currentBreakpoint = null;

    const checkBreakpoint = () => {
      const { width } = el.getBoundingClientRect();
      let newBreakpoint = null;

      const sortedBreakpoints = Object.entries(breakpoints)
        .sort(([, a], [, b]) => b - a);

      for (const [name, minWidth] of sortedBreakpoints) {
        if (width >= minWidth) {
          newBreakpoint = name;
          break;
        }
      }

      if (newBreakpoint !== currentBreakpoint) {
        const prevBreakpoint = currentBreakpoint;
        currentBreakpoint = newBreakpoint;
        handler(el, { current: currentBreakpoint, previous: prevBreakpoint, width });
      }
    };

    return onResize(el, checkBreakpoint, options);
  }

  function aspectRatioMaintainer(el, targetRatio, options = {}) {
    const { property = 'height', minSize = 0, maxSize = Infinity } = options;

    const maintain = () => {
      const rect = el.getBoundingClientRect();
      let newValue;

      if (property === 'height') {
        newValue = rect.width / targetRatio;
      } else {
        newValue = rect.height * targetRatio;
      }

      newValue = Math.max(minSize, Math.min(maxSize, newValue));
      el.style[property] = `${newValue}px`;
    };

    return onResize(el, maintain, { includeInitial: true, ...options });
  }

  function containerQueries(el, rules, options = {}) {
    const applyRules = () => {
      const { width, height } = el.getBoundingClientRect();

      rules.forEach(({ condition, className, styles }) => {
        let matches = false;

        if (typeof condition === 'function') {
          matches = condition({ width, height, el });
        } else if (typeof condition === 'object') {
          const { minWidth, maxWidth, minHeight, maxHeight } = condition;
          matches = true;

          if (minWidth !== undefined && width < minWidth) matches = false;
          if (maxWidth !== undefined && width > maxWidth) matches = false;
          if (minHeight !== undefined && height < minHeight) matches = false;
          if (maxHeight !== undefined && height > maxHeight) matches = false;
        }

        if (className) {
          el.classList.toggle(className, matches);
        }

        if (styles && matches) {
          Object.assign(el.style, styles);
        }
      });
    };

    return onResize(el, applyRules, { includeInitial: true, ...options });
  }

  // Expose utilities
  window.Resize = {
    onResize,
    onResizeMany,
    createResizeManager,
    responsiveBreakpoints,
    aspectRatioMaintainer,
    containerQueries
  };

})();