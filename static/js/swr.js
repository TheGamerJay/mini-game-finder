// SWR-Style Cache (Stale-While-Revalidate)
// Instant UI with background freshness

(function() {
  'use strict';

  const cache = new Map();
  const timestamps = new Map();
  const subscriptions = new Map();

  function swr(key, loader, options = {}) {
    const {
      ttl = 60000, // 1 minute default
      staleTime = 5000, // 5 seconds before considering stale
      retryCount = 3,
      retryDelay = 1000,
      onError = null,
      onSuccess = null,
      dedupe = true
    } = options;

    const now = Date.now();
    const cached = cache.get(key);
    const timestamp = timestamps.get(key) || 0;
    const age = now - timestamp;

    const isExpired = age > ttl;
    const isStale = age > staleTime;

    if (cached && !isExpired) {
      if (isStale && dedupe) {
        revalidateInBackground(key, loader, options);
      }
      return Promise.resolve(cached);
    }

    return loadWithRetry(key, loader, retryCount, retryDelay)
      .then(data => {
        cache.set(key, data);
        timestamps.set(key, Date.now());
        notifySubscribers(key, data);
        if (onSuccess) onSuccess(data);
        return data;
      })
      .catch(error => {
        if (cached) {
          if (onError) onError(error);
          return cached;
        }
        throw error;
      });
  }

  async function revalidateInBackground(key, loader, options) {
    const { retryCount = 3, retryDelay = 1000, onError, onSuccess } = options;

    try {
      const fresh = await loadWithRetry(key, loader, retryCount, retryDelay);
      cache.set(key, fresh);
      timestamps.set(key, Date.now());
      notifySubscribers(key, fresh);
      if (onSuccess) onSuccess(fresh);
    } catch (error) {
      if (onError) onError(error);
    }
  }

  async function loadWithRetry(key, loader, retryCount, retryDelay) {
    let lastError;

    for (let i = 0; i <= retryCount; i++) {
      try {
        return await loader();
      } catch (error) {
        lastError = error;
        if (i < retryCount) {
          await new Promise(resolve => setTimeout(resolve, retryDelay * Math.pow(2, i)));
        }
      }
    }

    throw lastError;
  }

  function notifySubscribers(key, data) {
    const keySubscribers = subscriptions.get(key);
    if (keySubscribers) {
      keySubscribers.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('SWR subscriber error:', error);
        }
      });
    }
  }

  function subscribe(key, callback) {
    if (!subscriptions.has(key)) {
      subscriptions.set(key, new Set());
    }
    subscriptions.get(key).add(callback);

    return () => {
      const keySubscribers = subscriptions.get(key);
      if (keySubscribers) {
        keySubscribers.delete(callback);
        if (keySubscribers.size === 0) {
          subscriptions.delete(key);
        }
      }
    };
  }

  function invalidate(key) {
    if (key) {
      cache.delete(key);
      timestamps.delete(key);
    } else {
      cache.clear();
      timestamps.clear();
    }
  }

  function preload(key, loader, options = {}) {
    if (!cache.has(key)) {
      swr(key, loader, options).catch(() => {});
    }
  }

  function mutate(key, data, shouldRevalidate = true) {
    cache.set(key, data);
    timestamps.set(key, Date.now());
    notifySubscribers(key, data);

    if (shouldRevalidate) {
      revalidateInBackground(key, () => Promise.resolve(data), {});
    }
  }

  function getCacheStats() {
    const now = Date.now();
    const stats = {
      totalEntries: cache.size,
      entries: []
    };

    for (const [key, data] of cache.entries()) {
      const timestamp = timestamps.get(key) || 0;
      const age = now - timestamp;

      stats.entries.push({
        key,
        age,
        size: JSON.stringify(data).length,
        subscribers: subscriptions.get(key)?.size || 0
      });
    }

    return stats;
  }

  function createSWRGroup(defaultOptions = {}) {
    return {
      get: (key, loader, options = {}) => swr(key, loader, { ...defaultOptions, ...options }),
      invalidate: invalidate,
      preload: (key, loader, options = {}) => preload(key, loader, { ...defaultOptions, ...options }),
      mutate: mutate,
      subscribe: subscribe
    };
  }

  function createBoundSWR(keyPrefix, defaultOptions = {}) {
    return {
      get: (key, loader, options = {}) => swr(`${keyPrefix}:${key}`, loader, { ...defaultOptions, ...options }),
      invalidate: (key) => invalidate(key ? `${keyPrefix}:${key}` : undefined),
      preload: (key, loader, options = {}) => preload(`${keyPrefix}:${key}`, loader, { ...defaultOptions, ...options }),
      mutate: (key, data, shouldRevalidate) => mutate(`${keyPrefix}:${key}`, data, shouldRevalidate),
      subscribe: (key, callback) => subscribe(`${keyPrefix}:${key}`, callback)
    };
  }

  function swrResource(url, options = {}) {
    const { fetcher = fetch, ...swrOptions } = options;

    return swr(url, () => fetcher(url).then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    }), swrOptions);
  }

  // Expose utilities
  window.SWR = {
    swr,
    subscribe,
    invalidate,
    preload,
    mutate,
    getCacheStats,
    createSWRGroup,
    createBoundSWR,
    swrResource
  };

})();