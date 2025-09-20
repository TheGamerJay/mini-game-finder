// Central Logger with Levels & Sampling
// Make prod debugging surgical (and quiet)

(function() {
  'use strict';

  const LEVELS = { debug: 10, info: 20, warn: 30, error: 40, fatal: 50 };

  const isDevelopment = () => {
    return location.hostname === "localhost" ||
           location.hostname === "127.0.0.1" ||
           location.hostname === "" ||
           location.port !== "";
  };

  const DEFAULT_LEVEL = isDevelopment() ? LEVELS.debug : LEVELS.info;

  let currentLevel = DEFAULT_LEVEL;
  let sampling = isDevelopment() ? 1.0 : 0.1;
  let contexts = new Set();
  let filters = [];

  function shouldLog(level, context = null, sampleRate = sampling) {
    if (level < currentLevel) return false;

    if (context && contexts.size > 0 && !contexts.has(context)) {
      return false;
    }

    if (filters.length > 0) {
      for (const filter of filters) {
        if (!filter(level, context)) return false;
      }
    }

    if (sampleRate < 1.0 && Math.random() > sampleRate) {
      return false;
    }

    return true;
  }

  function formatMessage(level, context, args) {
    const timestamp = new Date().toISOString();
    const levelName = Object.keys(LEVELS).find(key => LEVELS[key] === level) || 'UNKNOWN';
    const prefix = context ? `[${levelName}:${context}]` : `[${levelName}]`;

    if (isDevelopment()) {
      return [prefix, ...args];
    } else {
      return [`${timestamp} ${prefix}`, ...args];
    }
  }

  function createLogger(context = null) {
    return {
      debug: (...args) => {
        if (shouldLog(LEVELS.debug, context)) {
          console.debug(...formatMessage(LEVELS.debug, context, args));
        }
      },

      info: (...args) => {
        if (shouldLog(LEVELS.info, context)) {
          console.info(...formatMessage(LEVELS.info, context, args));
        }
      },

      warn: (...args) => {
        if (shouldLog(LEVELS.warn, context)) {
          console.warn(...formatMessage(LEVELS.warn, context, args));
        }
      },

      error: (...args) => {
        if (shouldLog(LEVELS.error, context)) {
          console.error(...formatMessage(LEVELS.error, context, args));
        }
      },

      fatal: (...args) => {
        console.error(...formatMessage(LEVELS.fatal, context, args));
      },

      time: (label) => {
        if (shouldLog(LEVELS.debug, context)) {
          console.time(context ? `${context}:${label}` : label);
        }
      },

      timeEnd: (label) => {
        if (shouldLog(LEVELS.debug, context)) {
          console.timeEnd(context ? `${context}:${label}` : label);
        }
      },

      group: (label) => {
        if (shouldLog(LEVELS.debug, context)) {
          console.group(...formatMessage(LEVELS.debug, context, [label]));
        }
      },

      groupEnd: () => {
        if (shouldLog(LEVELS.debug, context)) {
          console.groupEnd();
        }
      },

      trace: (...args) => {
        if (shouldLog(LEVELS.debug, context)) {
          console.trace(...formatMessage(LEVELS.debug, context, args));
        }
      }
    };
  }

  function setLevel(level) {
    if (typeof level === 'string') {
      currentLevel = LEVELS[level.toLowerCase()] || DEFAULT_LEVEL;
    } else if (typeof level === 'number') {
      currentLevel = level;
    }
  }

  function setSampling(rate) {
    sampling = Math.max(0, Math.min(1, rate));
  }

  function enableContexts(...contextNames) {
    contextNames.forEach(name => contexts.add(name));
  }

  function disableContexts(...contextNames) {
    contextNames.forEach(name => contexts.delete(name));
  }

  function clearContexts() {
    contexts.clear();
  }

  function addFilter(filterFn) {
    filters.push(filterFn);
    return () => {
      const index = filters.indexOf(filterFn);
      if (index > -1) filters.splice(index, 1);
    };
  }

  function createPerformanceLogger(context = 'PERF') {
    const logger = createLogger(context);

    return {
      measureFunction: (fn, label) => {
        return function measured(...args) {
          const start = performance.now();
          try {
            const result = fn.apply(this, args);

            if (result && typeof result.then === 'function') {
              return result.finally(() => {
                const duration = performance.now() - start;
                logger.debug(`${label} completed in ${duration.toFixed(2)}ms`);
              });
            }

            const duration = performance.now() - start;
            logger.debug(`${label} completed in ${duration.toFixed(2)}ms`);
            return result;

          } catch (error) {
            const duration = performance.now() - start;
            logger.error(`${label} failed after ${duration.toFixed(2)}ms:`, error);
            throw error;
          }
        };
      },

      measureAsync: async (fn, label) => {
        const start = performance.now();
        try {
          const result = await fn();
          const duration = performance.now() - start;
          logger.debug(`${label} completed in ${duration.toFixed(2)}ms`);
          return result;
        } catch (error) {
          const duration = performance.now() - start;
          logger.error(`${label} failed after ${duration.toFixed(2)}ms:`, error);
          throw error;
        }
      },

      mark: (name) => {
        performance.mark(name);
        logger.debug(`Performance mark: ${name}`);
      },

      measure: (name, startMark, endMark) => {
        performance.measure(name, startMark, endMark);
        const measure = performance.getEntriesByName(name, 'measure')[0];
        logger.debug(`Performance measure: ${name} = ${measure.duration.toFixed(2)}ms`);
      }
    };
  }

  const defaultLogger = createLogger();

  // Expose utilities
  window.Logger = {
    createLogger,
    createPerformanceLogger,
    setLevel,
    setSampling,
    enableContexts,
    disableContexts,
    clearContexts,
    addFilter,
    LEVELS,
    ...defaultLogger
  };

  // Global log for convenience
  window.log = defaultLogger;

})();