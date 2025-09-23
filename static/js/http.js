// Fetch Client with Retries, Backoff, and JSON Guard
// Turn flaky networks and shape drift into handled cases

(function() {
  'use strict';

  async function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async function getJSON(url, options = {}) {
    const {
      attempts = 3,
      signal,
      validate,
      backoffMs = 300,
      backoffFactor = 2,
      timeout = 10000,
      headers = {},
      ...fetchOptions
    } = options;

    let n = 0;
    let wait = backoffMs;

    while (true) {
      try {
        const controller = new AbortController();
        const combinedSignal = signal
          ? AbortSignal.any([signal, controller.signal])
          : controller.signal;

        const timeoutId = setTimeout(() => controller.abort(), timeout);

        const res = await fetch(url, {
          ...fetchOptions,
          signal: combinedSignal,
          credentials: 'include',
          headers: {
            "Accept": "application/json",
            "Content-Type": "application/json",
            ...headers
          }
        });

        clearTimeout(timeoutId);

        if (!res.ok) {
          const errorData = await res.text().catch(() => 'Unknown error');
          throw new Error(`HTTP ${res.status}: ${errorData}`);
        }

        const data = await res.json();

        if (validate && validate(data) !== true) {
          throw new Error("Schema validation failed");
        }

        return data;

      } catch (err) {
        n++;

        if (n >= attempts || (signal && signal.aborted)) {
          throw err;
        }

        console.warn(`[HTTP] Attempt ${n}/${attempts} failed for ${url}:`, err.message);
        await sleep(wait);
        wait *= backoffFactor;
      }
    }
  }

  async function postJSON(url, data, options = {}) {
    return getJSON(url, {
      method: 'POST',
      body: JSON.stringify(data),
      ...options
    });
  }

  async function putJSON(url, data, options = {}) {
    return getJSON(url, {
      method: 'PUT',
      body: JSON.stringify(data),
      ...options
    });
  }

  async function deleteJSON(url, options = {}) {
    return getJSON(url, {
      method: 'DELETE',
      ...options
    });
  }

  function createValidator(schema) {
    return function validate(data) {
      try {
        for (const [key, type] of Object.entries(schema)) {
          if (!(key in data)) {
            console.error(`Validation failed: missing key "${key}"`);
            return false;
          }

          const value = data[key];

          if (type === 'string' && typeof value !== 'string') {
            console.error(`Validation failed: "${key}" should be string, got ${typeof value}`);
            return false;
          }

          if (type === 'number' && typeof value !== 'number') {
            console.error(`Validation failed: "${key}" should be number, got ${typeof value}`);
            return false;
          }

          if (type === 'boolean' && typeof value !== 'boolean') {
            console.error(`Validation failed: "${key}" should be boolean, got ${typeof value}`);
            return false;
          }

          if (type === 'array' && !Array.isArray(value)) {
            console.error(`Validation failed: "${key}" should be array, got ${typeof value}`);
            return false;
          }

          if (typeof type === 'function' && !type(value)) {
            console.error(`Validation failed: "${key}" failed custom validation`);
            return false;
          }
        }
        return true;
      } catch (e) {
        console.error('Validation error:', e);
        return false;
      }
    };
  }

  function createHTTPClient(baseURL, defaultOptions = {}) {
    const client = {
      get: (path, options = {}) => getJSON(`${baseURL}${path}`, { ...defaultOptions, ...options }),
      post: (path, data, options = {}) => postJSON(`${baseURL}${path}`, data, { ...defaultOptions, ...options }),
      put: (path, data, options = {}) => putJSON(`${baseURL}${path}`, data, { ...defaultOptions, ...options }),
      delete: (path, options = {}) => deleteJSON(`${baseURL}${path}`, { ...defaultOptions, ...options })
    };

    return client;
  }

  // Expose utilities
  window.HTTP = {
    getJSON,
    postJSON,
    putJSON,
    deleteJSON,
    createValidator,
    createHTTPClient,
    sleep
  };

})();