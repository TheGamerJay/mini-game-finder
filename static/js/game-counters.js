// Professional Game Counter System - Isolated Per-Game Daily Usage
// Integrates with professional frontend architecture

(function() {
  'use strict';

  const logger = window.Logger.createLogger('GAME-COUNTERS');
  let lifecycle;
  let gameAPI;

  // Game counter configuration
  const GAME_CONFIGS = {
    wordfinder: { max: 5, price: 5, title: 'Mini Word Finder' },
    ttt: { max: 5, price: 5, title: 'Tic-Tac-Toe' },
    c4: { max: 5, price: 5, title: 'Connect 4' }
  };

  // Modal context for credit flow
  let modalContext = null;

  // Utility: local day key (uses the user's local time)
  function todayKey() {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  // Storage helpers with validation
  function storageKey(gameId) {
    if (!gameId) throw new Error('Game ID is required');
    return `usage:${gameId}:${todayKey()}`;
  }

  function readUsage(gameId) {
    try {
      const config = GAME_CONFIGS[gameId];
      if (!config) {
        logger.warn('Unknown game ID:', gameId);
        return { used: 0, max: 5, error: 'Unknown game' };
      }

      const raw = localStorage.getItem(storageKey(gameId));
      if (!raw) return { used: 0, max: config.max };

      const obj = JSON.parse(raw);
      return {
        used: Math.max(0, Number(obj.used) || 0),
        max: Math.max(1, Number(obj.max) || config.max)
      };
    } catch (error) {
      logger.error('Failed to read usage for', gameId, error);
      return { used: 0, max: GAME_CONFIGS[gameId]?.max || 5, error: error.message };
    }
  }

  function writeUsage(gameId, data) {
    try {
      const validated = {
        used: Math.max(0, Number(data.used) || 0),
        max: Math.max(1, Number(data.max) || 5),
        lastUpdated: Date.now()
      };

      localStorage.setItem(storageKey(gameId), JSON.stringify(validated));
      logger.debug('Usage updated for', gameId, validated);

      // Emit event for other components
      window.Bus.emit('game-counter:updated', { gameId, ...validated });

      return validated;
    } catch (error) {
      logger.error('Failed to write usage for', gameId, error);
      throw error;
    }
  }

  // Server integration with SWR caching
  async function syncUsageWithServer(gameId) {
    if (!gameAPI) return readUsage(gameId);

    try {
      const data = await window.SWR.swr(
        `game-usage-${gameId}`,
        () => gameAPI.get(`/usage/${gameId}`),
        {
          ttl: 60000, // 1 minute cache
          staleTime: 30000, // 30 seconds stale time
          onError: (error) => logger.warn('Server sync failed for', gameId, error.message)
        }
      );

      if (data && data.ok) {
        const serverUsage = {
          used: data.used || 0,
          max: data.max || GAME_CONFIGS[gameId]?.max || 5
        };

        // Merge with local data (take the maximum used count for safety)
        const localUsage = readUsage(gameId);
        const mergedUsage = {
          used: Math.max(localUsage.used, serverUsage.used),
          max: serverUsage.max
        };

        writeUsage(gameId, mergedUsage);
        return mergedUsage;
      }

      return readUsage(gameId);
    } catch (error) {
      logger.warn('Server sync failed, using local data:', error.message);
      return readUsage(gameId);
    }
  }

  // UI update with performance optimization
  function updateGameUI(card) {
    if (!card) return;

    const gameId = card.dataset.gameId;
    if (!gameId) {
      logger.warn('Game card missing data-game-id');
      return;
    }

    window.DOMBatch.batchWrites(() => {
      const usage = readUsage(gameId);
      const config = GAME_CONFIGS[gameId];

      // Update LCD display
      const lcd = window.Query.data('lcd', null, card);
      if (lcd) {
        lcd.textContent = `${usage.used} / ${usage.max}`;
      }

      // Update progress bar
      const bar = window.Query.data('bar', null, card);
      if (bar) {
        const percentage = Math.min(100, (usage.used / usage.max) * 100);
        bar.style.setProperty('--pct', `${percentage}%`);
      }

      // Update button state
      const useBtn = window.Query.data('action', 'use', card);
      if (useBtn) {
        useBtn.disabled = usage.used >= usage.max;
        window.Query.setState(useBtn, 'available', usage.used < usage.max);
      }

      // Update title and limits
      const titleEl = card.querySelector('h3');
      const limitEl = card.querySelector('.muted strong');
      if (titleEl && config) titleEl.textContent = config.title;
      if (limitEl) limitEl.textContent = usage.max;
    });

    logger.debug('UI updated for', gameId, readUsage(gameId));
  }

  // Try to use a game with validation and server sync
  async function tryUse(card) {
    const gameId = card.dataset.gameId;
    if (!gameId) {
      logger.error('Cannot use game: missing gameId');
      return { ok: false, error: 'Missing game ID' };
    }

    try {
      // Sync with server first if available
      const usage = await syncUsageWithServer(gameId);

      if (usage.used >= usage.max) {
        logger.info('Usage limit reached for', gameId, usage);
        return { ok: false, ...usage, reason: 'limit_reached' };
      }

      // Increment usage
      const newUsage = writeUsage(gameId, {
        used: usage.used + 1,
        max: usage.max
      });

      // Update UI
      updateGameUI(card);

      // Sync increment to server if available
      if (gameAPI) {
        window.Scheduler.whenIdle(() => {
          gameAPI.post(`/usage/${gameId}/increment`)
            .catch(error => logger.warn('Failed to sync increment to server:', error.message));
        });
      }

      logger.info('Game usage incremented for', gameId, newUsage);
      return { ok: true, ...newUsage };

    } catch (error) {
      logger.error('Failed to use game', gameId, error);
      return { ok: false, error: error.message };
    }
  }

  // Reset usage for development
  function resetUsage(gameId) {
    try {
      localStorage.removeItem(storageKey(gameId));
      window.SWR.invalidate(`game-usage-${gameId}`);

      // If server integration is available, reset on server too
      if (gameAPI) {
        gameAPI.post(`/usage/${gameId}/reset`)
          .catch(error => logger.warn('Failed to reset on server:', error.message));
      }

      logger.info('Usage reset for', gameId);
      window.Bus.emit('game-counter:reset', { gameId });

    } catch (error) {
      logger.error('Failed to reset usage for', gameId, error);
    }
  }

  // Modal management with proper lifecycle
  function openLimitModal({ gameId, card }) {
    const config = GAME_CONFIGS[gameId];
    if (!config) {
      logger.error('Cannot open modal: unknown game', gameId);
      return;
    }

    modalContext = { gameId, card, config };

    const modal = window.Query.$('#limitModal');
    const titleEl = window.Query.$('#modalGameTitle');
    const priceEl = window.Query.$('#modalPrice');

    if (modal && titleEl && priceEl) {
      window.DOMBatch.batchWrites(() => {
        titleEl.textContent = config.title;
        priceEl.textContent = config.price;
        modal.style.display = 'grid';
        window.Query.setState(modal, 'open', true);
      });

      logger.info('Limit modal opened for', gameId);
      window.Bus.emit('modal:opened', { type: 'limit', gameId });
    }
  }

  function closeLimitModal() {
    const modal = window.Query.$('#limitModal');
    if (modal) {
      window.DOMBatch.batchWrites(() => {
        modal.style.display = 'none';
        window.Query.setState(modal, 'open', false);
      });
    }

    if (modalContext) {
      logger.info('Limit modal closed for', modalContext.gameId);
      window.Bus.emit('modal:closed', { type: 'limit', gameId: modalContext.gameId });
    }

    modalContext = null;
  }

  // Credit flow integration
  async function startCreditFlow(context) {
    if (!context) {
      logger.error('Cannot start credit flow: no context');
      return;
    }

    const { gameId, config } = context;

    try {
      logger.info('Starting credit flow for', gameId, { price: config.price });

      // TODO: Replace with real credit system integration
      // Example: Stripe, PayPal, or internal credit system
      if (gameAPI) {
        const result = await gameAPI.post('/credits/consume', {
          gameId,
          amount: config.price
        });

        if (result.ok) {
          // Grant additional usage
          const usage = readUsage(gameId);
          writeUsage(gameId, {
            used: Math.max(0, usage.used - 1), // Allow one more use
            max: usage.max
          });

          updateGameUI(context.card);
          logger.info('Credit flow completed successfully for', gameId);
          window.Bus.emit('credits:consumed', { gameId, amount: config.price });
          return { ok: true };
        }
      } else {
        // Development mode: simulate credit purchase
        window.Scheduler.asap(() => {
          alert(`(DEV) Would consume ${config.price} credits for ${config.title}`);

          // Simulate successful purchase
          const usage = readUsage(gameId);
          writeUsage(gameId, {
            used: Math.max(0, usage.used - 1),
            max: usage.max
          });

          updateGameUI(context.card);
        });

        return { ok: true };
      }

    } catch (error) {
      logger.error('Credit flow failed for', gameId, error);
      window.Bus.emit('credits:error', { gameId, error: error.message });
      return { ok: false, error: error.message };
    }
  }

  // Event handlers with delegation and guards
  function setupEventHandlers() {
    const gamesContainer = window.Query.$('#games');
    if (!gamesContainer) {
      logger.warn('Games container not found');
      return;
    }

    // Game action delegation with guards
    lifecycle.addCleanup(
      window.Delegate.delegate(gamesContainer, 'click', '[data-action]',
        window.NavGuard.guardedClick(async (e, target) => {
          const card = target.closest('.game');
          if (!card) return;

          const action = target.dataset.action;
          const gameId = card.dataset.gameId;

          logger.debug('Game action triggered:', { action, gameId });

          if (action === 'use') {
            const result = await tryUse(card);

            if (!result.ok && result.reason === 'limit_reached') {
              openLimitModal({ gameId, card });
            } else if (result.ok) {
              // Emit event for game to start
              window.Bus.emit('game:use-requested', { gameId, card });
            }
          } else if (action === 'reset') {
            resetUsage(gameId);
            updateGameUI(card);
          }
        }, { key: 'game-action' })
      )
    );

    // Modal handlers
    const modalCancel = window.Query.$('#modalCancel');
    const modalContinue = window.Query.$('#modalContinue');

    if (modalCancel) {
      lifecycle.addCleanup(
        window.Delegate.delegate(modalCancel, 'click', '', () => closeLimitModal())
      );
    }

    if (modalContinue) {
      lifecycle.addCleanup(
        window.Delegate.delegate(modalContinue, 'click', '',
          window.NavGuard.guardedClick(async () => {
            if (modalContext) {
              await startCreditFlow(modalContext);
              closeLimitModal();
            }
          }, { key: 'credit-flow' })
        )
      );
    }

    logger.debug('Event handlers setup complete');
  }

  // Initialize all game cards
  function initializeGameCards() {
    const gameCards = window.Query.$$('.game[data-game-id]');

    gameCards.forEach(card => {
      const gameId = card.dataset.gameId;

      // Add performance classes
      card.classList.add('game-counter-card');

      // Sync with server if available
      if (gameAPI) {
        syncUsageWithServer(gameId)
          .then(() => updateGameUI(card))
          .catch(error => {
            logger.warn('Initial sync failed for', gameId, error.message);
            updateGameUI(card); // Use local data
          });
      } else {
        updateGameUI(card);
      }
    });

    logger.info('Game cards initialized:', gameCards.length);
  }

  // Professional initialization
  function init() {
    lifecycle = window.Lifecycles.createLifecycle();

    // Initialize HTTP client if available
    if (window.HTTP) {
      gameAPI = window.HTTP.createHTTPClient('/api', {
        timeout: 5000,
        attempts: 2
      });
    }

    setupEventHandlers();
    initializeGameCards();

    // Subscribe to global events
    lifecycle.addCleanup(
      window.Bus.on('game:reload-counters', () => {
        window.Query.$$('.game[data-game-id]').forEach(updateGameUI);
      })
    );

    lifecycle.addCleanup(
      window.Bus.on('credits:purchased', (data) => {
        if (data.gameId) {
          const card = window.Query.$(`[data-game-id="${data.gameId}"]`);
          if (card) updateGameUI(card);
        }
      })
    );

    logger.info('Game counter system initialized');
    window.Bus.emit('game-counters:ready');
  }

  // Public API
  window.GameCounters = {
    readUsage,
    writeUsage,
    resetUsage,
    tryUse,
    updateGameUI,
    syncUsageWithServer,
    GAME_CONFIGS
  };

  // Auto-initialize when DOM is ready
  window.DOMReady.onDomReady(init);

})();