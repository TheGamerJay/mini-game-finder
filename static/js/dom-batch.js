// Render/Bind Order Guard (RAF + microtask batching)
// Avoid layout thrash and "DOM not there yet" races

(function() {
  'use strict';

  function afterRender(cb) {
    requestAnimationFrame(() => queueMicrotask(cb));
  }

  function batchReads(cb) {
    requestAnimationFrame(cb);
  }

  function batchWrites(cb) {
    requestAnimationFrame(() => requestAnimationFrame(cb));
  }

  function batchReadWrites(readCb, writeCb) {
    requestAnimationFrame(() => {
      const measurements = readCb();
      requestAnimationFrame(() => writeCb(measurements));
    });
  }

  let pendingBatchedUpdates = new Set();
  let batchUpdateScheduled = false;

  function batchedUpdate(key, updateFn) {
    pendingBatchedUpdates.set(key, updateFn);

    if (!batchUpdateScheduled) {
      batchUpdateScheduled = true;
      requestAnimationFrame(() => {
        const updates = new Map(pendingBatchedUpdates);
        pendingBatchedUpdates.clear();
        batchUpdateScheduled = false;

        updates.forEach((updateFn, key) => {
          try {
            updateFn();
          } catch (e) {
            console.error(`Batched update error for key "${key}":`, e);
          }
        });
      });
    }
  }

  function deferredRender(renderFn, priority = 'normal') {
    const priorities = {
      immediate: () => queueMicrotask(renderFn),
      normal: () => requestAnimationFrame(renderFn),
      low: () => requestAnimationFrame(() => requestAnimationFrame(renderFn)),
      idle: () => {
        const fn = window.requestIdleCallback || setTimeout;
        fn(renderFn, { timeout: 1000 });
      }
    };

    (priorities[priority] || priorities.normal)();
  }

  function createRenderQueue() {
    const queue = [];
    let processing = false;

    function process() {
      if (processing || queue.length === 0) return;

      processing = true;
      requestAnimationFrame(() => {
        const batch = queue.splice(0);

        batch.forEach(({ type, fn, priority }) => {
          try {
            if (type === 'read') {
              fn();
            }
          } catch (e) {
            console.error('Render queue read error:', e);
          }
        });

        requestAnimationFrame(() => {
          batch.forEach(({ type, fn }) => {
            try {
              if (type === 'write') {
                fn();
              }
            } catch (e) {
              console.error('Render queue write error:', e);
            }
          });

          processing = false;
          if (queue.length > 0) {
            process();
          }
        });
      });
    }

    return {
      read(fn, priority = 'normal') {
        queue.push({ type: 'read', fn, priority });
        process();
      },

      write(fn, priority = 'normal') {
        queue.push({ type: 'write', fn, priority });
        process();
      },

      clear() {
        queue.length = 0;
      }
    };
  }

  // Expose utilities
  window.DOMBatch = {
    afterRender,
    batchReads,
    batchWrites,
    batchReadWrites,
    batchedUpdate,
    deferredRender,
    createRenderQueue
  };

})();