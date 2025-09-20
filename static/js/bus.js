// Tiny Pub/Sub (Decouple Modules Without Global Soup)
// Modules talk via events, not imports everywhere

(function() {
  'use strict';

  const listeners = new Map();
  const onceListeners = new Map();
  const wildcardListeners = new Set();
  let eventHistory = [];
  const maxHistorySize = 100;

  function on(event, handler, options = {}) {
    const { once = false, priority = 0 } = options;

    if (once) {
      if (!onceListeners.has(event)) {
        onceListeners.set(event, new Set());
      }
      const wrappedHandler = (...args) => {
        onceListeners.get(event).delete(wrappedHandler);
        handler(...args);
      };
      onceListeners.get(event).add(wrappedHandler);
      return () => onceListeners.get(event)?.delete(wrappedHandler);
    }

    if (!listeners.has(event)) {
      listeners.set(event, []);
    }

    const entry = { handler, priority };
    const eventListeners = listeners.get(event);

    const insertIndex = eventListeners.findIndex(item => item.priority < priority);
    if (insertIndex === -1) {
      eventListeners.push(entry);
    } else {
      eventListeners.splice(insertIndex, 0, entry);
    }

    return () => {
      const eventListeners = listeners.get(event);
      if (eventListeners) {
        const index = eventListeners.findIndex(item => item.handler === handler);
        if (index > -1) {
          eventListeners.splice(index, 1);
          if (eventListeners.length === 0) {
            listeners.delete(event);
          }
        }
      }
    };
  }

  function once(event, handler, options = {}) {
    return on(event, handler, { ...options, once: true });
  }

  function off(event, handler) {
    if (!handler) {
      listeners.delete(event);
      onceListeners.delete(event);
      return;
    }

    const eventListeners = listeners.get(event);
    if (eventListeners) {
      const index = eventListeners.findIndex(item => item.handler === handler);
      if (index > -1) {
        eventListeners.splice(index, 1);
        if (eventListeners.length === 0) {
          listeners.delete(event);
        }
      }
    }

    const eventOnceListeners = onceListeners.get(event);
    if (eventOnceListeners) {
      eventOnceListeners.delete(handler);
      if (eventOnceListeners.size === 0) {
        onceListeners.delete(event);
      }
    }
  }

  function emit(event, payload, options = {}) {
    const { sync = true, bubbles = false } = options;
    const timestamp = Date.now();

    eventHistory.push({ event, payload, timestamp });
    if (eventHistory.length > maxHistorySize) {
      eventHistory.shift();
    }

    const executeHandlers = () => {
      const eventListeners = listeners.get(event) || [];
      const eventOnceListeners = onceListeners.get(event) || new Set();

      const allHandlers = [
        ...eventListeners.map(item => item.handler),
        ...eventOnceListeners
      ];

      for (const handler of allHandlers) {
        try {
          handler(payload, { event, timestamp });
        } catch (error) {
          console.error(`Event handler error for "${event}":`, error);
        }
      }

      onceListeners.delete(event);

      for (const wildcardHandler of wildcardListeners) {
        try {
          wildcardHandler(event, payload, { timestamp });
        } catch (error) {
          console.error(`Wildcard handler error for "${event}":`, error);
        }
      }

      if (bubbles) {
        const parts = event.split(':');
        for (let i = parts.length - 1; i > 0; i--) {
          const parentEvent = parts.slice(0, i).join(':');
          emit(parentEvent, payload, { sync, bubbles: false });
        }
      }
    };

    if (sync) {
      executeHandlers();
    } else {
      setTimeout(executeHandlers, 0);
    }
  }

  function onWildcard(handler) {
    wildcardListeners.add(handler);
    return () => wildcardListeners.delete(handler);
  }

  function createNamespace(prefix) {
    return {
      on: (event, handler, options) => on(`${prefix}:${event}`, handler, options),
      once: (event, handler, options) => once(`${prefix}:${event}`, handler, options),
      off: (event, handler) => off(`${prefix}:${event}`, handler),
      emit: (event, payload, options) => emit(`${prefix}:${event}`, payload, options)
    };
  }

  function waitFor(event, timeout = 5000) {
    return new Promise((resolve, reject) => {
      const timer = timeout > 0 ? setTimeout(() => {
        off(event, handler);
        reject(new Error(`Event "${event}" timeout after ${timeout}ms`));
      }, timeout) : null;

      const handler = (payload, meta) => {
        if (timer) clearTimeout(timer);
        resolve({ payload, meta });
      };

      once(event, handler);
    });
  }

  function createEventGroup() {
    const subscriptions = [];

    return {
      on: (event, handler, options) => {
        const unsubscribe = on(event, handler, options);
        subscriptions.push(unsubscribe);
        return unsubscribe;
      },

      once: (event, handler, options) => {
        const unsubscribe = once(event, handler, options);
        subscriptions.push(unsubscribe);
        return unsubscribe;
      },

      emit: emit,

      destroy: () => {
        subscriptions.forEach(unsubscribe => unsubscribe());
        subscriptions.length = 0;
      }
    };
  }

  function getEventStats() {
    const stats = {
      activeListeners: listeners.size,
      onceListeners: onceListeners.size,
      wildcardListeners: wildcardListeners.size,
      historySize: eventHistory.length,
      events: {}
    };

    for (const [event, handlers] of listeners.entries()) {
      stats.events[event] = handlers.length;
    }

    return stats;
  }

  function getEventHistory(filter = null) {
    if (!filter) return [...eventHistory];

    if (typeof filter === 'string') {
      return eventHistory.filter(entry => entry.event === filter);
    }

    if (typeof filter === 'function') {
      return eventHistory.filter(filter);
    }

    return [...eventHistory];
  }

  function clearEventHistory() {
    eventHistory.length = 0;
  }

  function replay(eventFilter = null, delayMs = 0) {
    const events = getEventHistory(eventFilter);

    events.forEach((entry, index) => {
      setTimeout(() => {
        emit(entry.event, entry.payload, { sync: false });
      }, index * delayMs);
    });
  }

  // Expose utilities
  window.Bus = {
    on,
    once,
    off,
    emit,
    onWildcard,
    createNamespace,
    waitFor,
    createEventGroup,
    getEventStats,
    getEventHistory,
    clearEventHistory,
    replay
  };

})();