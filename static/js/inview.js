// Viewport-Only Activation (IntersectionObserver)
// Only initialize widgets that are actually visible

(function() {
  'use strict';

  function onEnterViewport(el, cb, options = {}) {
    const defaultOptions = {
      root: null,
      rootMargin: '0px',
      threshold: 0.1
    };

    const observerOptions = { ...defaultOptions, ...options };

    const io = new IntersectionObserver(entries => {
      const entry = entries.find(e => e.target === el);
      if (entry && entry.isIntersecting) {
        io.disconnect();
        cb(el, entry);
      }
    }, observerOptions);

    io.observe(el);

    return () => io.disconnect();
  }

  function onExitViewport(el, cb, options = {}) {
    const defaultOptions = {
      root: null,
      rootMargin: '0px',
      threshold: 0
    };

    const observerOptions = { ...defaultOptions, ...options };

    const io = new IntersectionObserver(entries => {
      const entry = entries.find(e => e.target === el);
      if (entry && !entry.isIntersecting) {
        cb(el, entry);
      }
    }, observerOptions);

    io.observe(el);

    return () => io.disconnect();
  }

  function onViewportChange(el, callbacks, options = {}) {
    const { onEnter, onExit, onVisible, onHidden } = callbacks;
    const defaultOptions = {
      root: null,
      rootMargin: '0px',
      threshold: [0, 0.1, 0.5, 1.0]
    };

    const observerOptions = { ...defaultOptions, ...options };

    const io = new IntersectionObserver(entries => {
      const entry = entries.find(e => e.target === el);
      if (!entry) return;

      const wasVisible = el.dataset._wasVisible === 'true';
      const isVisible = entry.isIntersecting;

      if (!wasVisible && isVisible) {
        el.dataset._wasVisible = 'true';
        if (onEnter) onEnter(el, entry);
        if (onVisible) onVisible(el, entry);
      } else if (wasVisible && !isVisible) {
        el.dataset._wasVisible = 'false';
        if (onExit) onExit(el, entry);
        if (onHidden) onHidden(el, entry);
      }
    }, observerOptions);

    io.observe(el);

    return () => {
      io.disconnect();
      delete el.dataset._wasVisible;
    };
  }

  function lazyInit(selector, initFn, options = {}) {
    const elements = document.querySelectorAll(selector);
    const teardowns = [];

    elements.forEach(el => {
      const teardown = onEnterViewport(el, (element) => {
        try {
          initFn(element);
          element.dataset._lazyInited = 'true';
        } catch (e) {
          console.error('Lazy init error:', e);
        }
      }, options);

      teardowns.push(teardown);
    });

    return () => teardowns.forEach(fn => fn());
  }

  function createViewportManager() {
    const observers = new Map();
    const elements = new Map();

    return {
      observe(el, callbacks, options = {}) {
        if (elements.has(el)) {
          this.unobserve(el);
        }

        const teardown = onViewportChange(el, callbacks, options);
        elements.set(el, teardown);

        return () => this.unobserve(el);
      },

      unobserve(el) {
        const teardown = elements.get(el);
        if (teardown) {
          teardown();
          elements.delete(el);
        }
      },

      observeMany(selector, callbacks, options = {}) {
        const elements = document.querySelectorAll(selector);
        const teardowns = [];

        elements.forEach(el => {
          const teardown = this.observe(el, callbacks, options);
          teardowns.push(teardown);
        });

        return () => teardowns.forEach(fn => fn());
      },

      clear() {
        elements.forEach((teardown, el) => teardown());
        elements.clear();
      }
    };
  }

  function visibilityGate(el, threshold = 0.5) {
    return new Promise(resolve => {
      const teardown = onEnterViewport(el, (element, entry) => {
        resolve({ element, entry });
      }, { threshold });

      setTimeout(() => {
        teardown();
        resolve(null);
      }, 10000);
    });
  }

  // Expose utilities
  window.InView = {
    onEnterViewport,
    onExitViewport,
    onViewportChange,
    lazyInit,
    createViewportManager,
    visibilityGate
  };

})();