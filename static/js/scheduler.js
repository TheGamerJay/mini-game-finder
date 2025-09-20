// Idle & Priority Work Split
// Keep the UI snappy by deferring non-urgent tasks

(function() {
  'use strict';

  function asap(cb) {
    queueMicrotask(cb);
  }

  function afterFrame(cb) {
    requestAnimationFrame(cb);
  }

  function whenIdle(cb, timeout = 1500) {
    const fn = window.requestIdleCallback || ((f) =>
      setTimeout(() => f({ didTimeout: true, timeRemaining: () => 0 }), timeout)
    );

    return fn(cb, { timeout });
  }

  function createTaskScheduler() {
    const queues = {
      immediate: [],
      high: [],
      normal: [],
      low: [],
      idle: []
    };

    let processing = false;

    function process() {
      if (processing) return;
      processing = true;

      asap(() => {
        while (queues.immediate.length > 0) {
          const task = queues.immediate.shift();
          try {
            task();
          } catch (e) {
            console.error('Immediate task error:', e);
          }
        }

        afterFrame(() => {
          const start = performance.now();
          const timeSlice = 5; // ms

          while (queues.high.length > 0 && (performance.now() - start) < timeSlice) {
            const task = queues.high.shift();
            try {
              task();
            } catch (e) {
              console.error('High priority task error:', e);
            }
          }

          afterFrame(() => {
            const normalStart = performance.now();

            while (queues.normal.length > 0 && (performance.now() - normalStart) < timeSlice) {
              const task = queues.normal.shift();
              try {
                task();
              } catch (e) {
                console.error('Normal priority task error:', e);
              }
            }

            whenIdle((deadline) => {
              while (queues.low.length > 0 && deadline.timeRemaining() > 1) {
                const task = queues.low.shift();
                try {
                  task();
                } catch (e) {
                  console.error('Low priority task error:', e);
                }
              }

              while (queues.idle.length > 0 && deadline.timeRemaining() > 1) {
                const task = queues.idle.shift();
                try {
                  task();
                } catch (e) {
                  console.error('Idle task error:', e);
                }
              }

              processing = false;

              if (Object.values(queues).some(q => q.length > 0)) {
                process();
              }
            });
          });
        });
      });
    }

    return {
      schedule(task, priority = 'normal') {
        if (!queues[priority]) {
          console.warn(`Unknown priority "${priority}", using "normal"`);
          priority = 'normal';
        }

        queues[priority].push(task);
        process();
      },

      clear(priority) {
        if (priority) {
          queues[priority].length = 0;
        } else {
          Object.keys(queues).forEach(key => {
            queues[key].length = 0;
          });
        }
      },

      stats() {
        return Object.entries(queues).reduce((acc, [priority, queue]) => {
          acc[priority] = queue.length;
          return acc;
        }, {});
      }
    };
  }

  function debounce(fn, ms, immediate = false) {
    let timeoutId;
    let lastCallTime = 0;

    return function debounced(...args) {
      const now = Date.now();
      const timeSinceLastCall = now - lastCallTime;

      const execute = () => {
        lastCallTime = now;
        fn.apply(this, args);
      };

      if (immediate && timeSinceLastCall > ms) {
        execute();
      } else {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(execute, ms);
      }
    };
  }

  function throttle(fn, ms) {
    let lastCallTime = 0;
    let timeoutId;

    return function throttled(...args) {
      const now = Date.now();
      const timeSinceLastCall = now - lastCallTime;

      if (timeSinceLastCall >= ms) {
        lastCallTime = now;
        fn.apply(this, args);
      } else {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
          lastCallTime = Date.now();
          fn.apply(this, args);
        }, ms - timeSinceLastCall);
      }
    };
  }

  // Expose utilities
  window.Scheduler = {
    asap,
    afterFrame,
    whenIdle,
    createTaskScheduler,
    debounce,
    throttle
  };

})();