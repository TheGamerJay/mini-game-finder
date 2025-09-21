// 🖼 Block C — Frontend: Credits Management System
// This module handles credit balance display, game start flow, and reveal functionality

(function() {
  'use strict';

  // Improved API helper function with better CSRF handling
  async function fetchJSON(url, bodyObj = null, opts = {}) {
    const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    const defaultOpts = {
      method: bodyObj ? 'POST' : 'GET',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrf
      },
      ...opts
    };

    if (bodyObj) {
      defaultOpts.body = JSON.stringify(bodyObj);
    }

    const response = await fetch(url, defaultOpts);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    return response.json();
  }

  // Credit balance management
  class CreditsManager {
    constructor() {
      this.currentBalance = 0;
      this.balanceElement = null;
      this.callbacks = [];
    }

    init() {
      // Find credit balance element
      this.balanceElement = document.getElementById('credit-badge') ||
                           document.getElementById('wallet') ||
                           this.createBalanceElement();

      // Initial balance fetch
      this.refreshBalance();

      // Set up periodic refresh (every 30 seconds)
      setInterval(() => this.refreshBalance(), 30000);
    }

    createBalanceElement() {
      // Create credit badge if it doesn't exist
      const badge = document.createElement('div');
      badge.id = 'credit-badge';
      badge.className = 'credit-badge';
      badge.innerHTML = 'Credits: <span class="credit-amount">--</span>';

      // Try to add to header or create floating badge
      const header = document.querySelector('header, .header, nav, .nav');
      if (header) {
        header.appendChild(badge);
      } else {
        // Create floating badge
        badge.style.cssText = `
          position: fixed;
          top: 20px;
          right: 20px;
          background: #1f2937;
          color: #f3f4f6;
          padding: 8px 16px;
          border-radius: 20px;
          font-size: 14px;
          font-weight: bold;
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
          z-index: 1000;
          border: 1px solid #374151;
        `;
        document.body.appendChild(badge);
      }

      return badge;
    }

    async refreshBalance() {
      try {
        const data = await fetchJSON('/api/credits/balance');
        this.updateBalance(data.balance);
      } catch (error) {
        console.warn('Failed to refresh credit balance:', error);
        // Don't show error to user for background refresh
      }
    }

    updateBalance(newBalance) {
      this.currentBalance = newBalance;

      if (this.balanceElement) {
        const amountElement = this.balanceElement.querySelector('.credit-amount');
        if (amountElement) {
          amountElement.textContent = newBalance;
        } else {
          this.balanceElement.textContent = `Credits: ${newBalance}`;
        }
      }

      // Notify callbacks
      this.callbacks.forEach(callback => {
        try {
          callback(newBalance);
        } catch (error) {
          console.error('Credit balance callback error:', error);
        }
      });
    }

    onBalanceChange(callback) {
      this.callbacks.push(callback);
    }

    getBalance() {
      return this.currentBalance;
    }

    async spendCredits(amount, reason, puzzleId = null, wordId = null) {
      // This is handled by the API, but we can predict the new balance
      const newBalance = Math.max(0, this.currentBalance - amount);
      this.updateBalance(newBalance);

      // The actual spending will be done by the API endpoints
      // This is just for UI responsiveness
    }
  }

  // Game start flow manager
  class GameManager {
    constructor(creditsManager) {
      this.credits = creditsManager;
      this.currentPuzzleId = null;
      this.currentSessionId = null;
      this.gameMode = 'easy';
      this.isGameActive = false;
    }

    init() {
      this.bindStartGameButtons();
      this.loadGameCosts();
    }

    async loadGameCosts() {
      try {
        const data = await fetchJSON('/api/game/costs');
        this.gameCosts = data.costs;
        this.userGameInfo = data.user;

        // Update UI with cost information
        this.updateCostDisplay();
      } catch (error) {
        console.error('Failed to load game costs:', error);
      }
    }

    updateCostDisplay() {
      // Update start game button text with cost info
      const startButtons = document.querySelectorAll('[data-action="start-game"], #startGameBtn');

      startButtons.forEach(button => {
        const costSpan = button.querySelector('.btn-cost');
        const hasFreeGames = this.userGameInfo && this.userGameInfo.free_games_remaining > 0;

        if (costSpan) {
          // New game card style buttons
          if (hasFreeGames) {
            costSpan.textContent = `${this.userGameInfo.free_games_remaining} free remaining`;
            button.classList.add('free');
            button.classList.remove('cost-required');
          } else {
            costSpan.textContent = `${this.gameCosts?.game_start || 5} credits`;
            button.classList.remove('free');
            button.classList.add('cost-required');
          }
        } else {
          // Legacy button style
          if (hasFreeGames) {
            button.textContent = `Start Game (${this.userGameInfo.free_games_remaining} free remaining)`;
            button.classList.remove('cost-required');
          } else {
            button.textContent = `Start Game (${this.gameCosts?.game_start || 5} credits)`;
            button.classList.add('cost-required');
          }
        }
      });
    }

    bindStartGameButtons() {
      // Bind to existing start game buttons
      const startButtons = document.querySelectorAll('[data-action="start-game"], #startGameBtn');

      startButtons.forEach(button => {
        button.addEventListener('click', (event) => {
          event.preventDefault();
          this.handleStartGame(button);
        });
      });

      // Also bind to play links that might exist
      const playLinks = document.querySelectorAll('a[href*="/play/"]');
      playLinks.forEach(link => {
        link.addEventListener('click', (event) => {
          event.preventDefault();
          const mode = link.href.match(/\/play\/(\w+)/)?.[1] || 'easy';
          this.startGame(mode);
        });
      });
    }

    async handleStartGame(button) {
      // Get game mode from button or current page
      this.gameMode = button.dataset.mode ||
                    document.querySelector('#meta')?.dataset.mode ||
                    'easy';

      // Get puzzle ID if available
      this.currentPuzzleId = window.CURRENT_PUZZLE_ID ||
                            button.dataset.puzzleId ||
                            Math.floor(Math.random() * 1000000);

      await this.startGame(this.gameMode);
    }

    async startGame(mode = 'easy') {
      try {
        // Show loading state
        this.setStartButtonState('loading');

        const requestData = {
          puzzle_id: this.currentPuzzleId,
          mode: mode,
          category: document.querySelector('#meta')?.dataset.category || null
        };

        console.log('Starting game:', requestData);

        const response = await fetchJSON('/api/game/start', {
          method: 'POST',
          body: JSON.stringify(requestData)
        });

        if (response.ok) {
          // Game started successfully
          this.currentSessionId = response.session_id;
          this.isGameActive = true;

          // Update credit balance
          this.credits.updateBalance(response.balance);

          // Update cost display
          this.userGameInfo = {
            free_games_remaining: response.free_games_remaining,
            balance: response.balance
          };
          this.updateCostDisplay();

          // Show success message
          if (response.paid) {
            this.showMessage(`Game started! Charged ${response.cost} credits.`, 'success');
          } else {
            this.showMessage(`Free game started! ${response.free_games_remaining} free games remaining.`, 'success');
          }

          // Start the actual puzzle game
          this.startPuzzleGame();

        } else {
          throw new Error(response.error || 'Failed to start game');
        }

      } catch (error) {
        console.error('Game start error:', error);

        if (error.message.includes('INSUFFICIENT_CREDITS')) {
          this.handleInsufficientCredits();
        } else {
          this.showMessage(`Failed to start game: ${error.message}`, 'error');
        }
      } finally {
        this.setStartButtonState('ready');
      }
    }

    handleInsufficientCredits() {
      this.showMessage('You need more credits to start a game.', 'error');

      // Show store modal or redirect to store
      if (window.openStoreModal) {
        window.openStoreModal();
      } else {
        const storeUrl = '/store';
        this.showMessage(
          `<a href="${storeUrl}" class="store-link">Visit the Store to buy credits</a>`,
          'info'
        );
      }
    }

    startPuzzleGame() {
      // Start the actual puzzle game logic
      if (window.startPuzzle) {
        window.startPuzzle();
      } else if (window.loadPuzzle) {
        window.loadPuzzle();
      } else {
        // Fallback: reload the page to start the game
        const gameUrl = `/play/${this.gameMode}`;
        window.location.href = gameUrl;
      }
    }

    setStartButtonState(state) {
      const startButtons = document.querySelectorAll('[data-action="start-game"], #startGameBtn');

      startButtons.forEach(button => {
        const btnText = button.querySelector('.btn-text');
        const btnCost = button.querySelector('.btn-cost');

        switch (state) {
          case 'loading':
            button.disabled = true;
            button.classList.add('loading');

            if (btnText) {
              // New game card style
              button.dataset.originalText = btnText.textContent;
              btnText.textContent = 'Starting';
            } else {
              // Legacy button style
              button.dataset.originalText = button.textContent;
              button.textContent = 'Starting...';
            }
            break;

          case 'ready':
            button.disabled = false;
            button.classList.remove('loading');

            if (btnText && button.dataset.originalText) {
              // New game card style
              btnText.textContent = button.dataset.originalText;
              delete button.dataset.originalText;
            } else if (button.dataset.originalText) {
              // Legacy button style
              button.textContent = button.dataset.originalText;
              delete button.dataset.originalText;
            }
            break;
        }
      });
    }

    showMessage(message, type = 'info') {
      // Create or update message display
      let messageEl = document.getElementById('game-message');

      if (!messageEl) {
        messageEl = document.createElement('div');
        messageEl.id = 'game-message';
        messageEl.style.cssText = `
          position: fixed;
          top: 80px;
          right: 20px;
          max-width: 300px;
          padding: 12px 16px;
          border-radius: 8px;
          font-size: 14px;
          z-index: 1001;
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
          transition: opacity 0.3s ease;
        `;
        document.body.appendChild(messageEl);
      }

      // Set message style based on type
      const styles = {
        success: 'background: #065f46; color: #d1fae5; border-left: 4px solid #10b981;',
        error: 'background: #7f1d1d; color: #fee2e2; border-left: 4px solid #ef4444;',
        info: 'background: #1e3a8a; color: #dbeafe; border-left: 4px solid #3b82f6;'
      };

      messageEl.style.cssText += styles[type] || styles.info;
      messageEl.innerHTML = message;
      messageEl.style.opacity = '1';

      // Auto-hide after 5 seconds
      setTimeout(() => {
        messageEl.style.opacity = '0';
        setTimeout(() => {
          if (messageEl.parentNode) {
            messageEl.parentNode.removeChild(messageEl);
          }
        }, 300);
      }, 5000);
    }

    async completeGame(wordsFound, totalWords, score) {
      if (!this.currentSessionId) return;

      try {
        await fetchJSON(`/api/game/session/${this.currentSessionId}/complete`, {
          method: 'POST',
          body: JSON.stringify({
            words_found: wordsFound,
            total_words: totalWords,
            score: score
          })
        });

        this.isGameActive = false;
        this.currentSessionId = null;

        console.log('Game session completed successfully');
      } catch (error) {
        console.error('Failed to complete game session:', error);
      }
    }
  }

  // Word reveal manager
  class RevealManager {
    constructor(creditsManager) {
      this.credits = creditsManager;
      this.revealCost = 5; // Will be loaded from API
    }

    init() {
      this.bindRevealButtons();
      this.loadRevealCost();
    }

    async loadRevealCost() {
      try {
        const data = await fetchJSON('/api/game/costs');
        this.revealCost = data.costs.word_reveal || 5;
        this.updateRevealButtonCosts();
      } catch (error) {
        console.error('Failed to load reveal cost:', error);
      }
    }

    updateRevealButtonCosts() {
      const revealButtons = document.querySelectorAll('[data-action="reveal"], .reveal-btn');
      revealButtons.forEach(button => {
        const costSpan = button.querySelector('.cost');
        if (costSpan) {
          costSpan.textContent = this.revealCost;
        } else {
          button.textContent = `Reveal (${this.revealCost})`;
        }
      });
    }

    bindRevealButtons() {
      // Use event delegation for dynamically created buttons
      document.addEventListener('click', (event) => {
        const button = event.target.closest('[data-action="reveal"], .reveal-btn');
        if (button) {
          event.preventDefault();
          this.handleRevealClick(button);
        }
      });
    }

    async handleRevealClick(button) {
      const puzzleId = button.dataset.puzzleId ||
                      window.CURRENT_PUZZLE_ID ||
                      document.querySelector('#meta')?.dataset.puzzleId;

      const wordId = button.dataset.wordId;

      if (!puzzleId || !wordId) {
        console.error('Missing puzzle_id or word_id for reveal');
        return;
      }

      // Check if user has enough credits
      if (this.credits.getBalance() < this.revealCost) {
        this.handleInsufficientCredits();
        return;
      }

      // Show confirmation dialog
      const confirmMessage = `Reveal this word for ${this.revealCost} credits? It will highlight and teach you.`;
      if (!confirm(confirmMessage)) {
        return;
      }

      // Use safeAction to prevent double clicks
      const safeAction = window.safeAction || this.fallbackSafeAction;
      await safeAction(button, async () => {
        button.textContent = 'Revealing...';

        // Use the new API system if available, fallback to fetchJSON
        let response;
        if (window.API && window.API.spendBackend) {
          response = await window.API.spendBackend(this.revealCost, 'reveal', {
            puzzle_id: puzzleId,
            word_id: wordId,
            game_session_id: window.currentGameSession?.id
          });
        } else {
          response = await fetchJSON('/api/game/reveal', {
            puzzle_id: puzzleId,
            word_id: wordId,
            game_session_id: window.currentGameSession?.id
          });
        }

        if (response.ok) {
          // Update credit balance (also handled by API wrapper)
          this.credits.updateBalance(response.balance);

          // Mark the word as found (this will update UI and save state)
          if (window.markFoundRevealed) {
            window.markFoundRevealed(wordId, response.path);
          }

          // Show lesson overlay
          if (response.lesson && window.showLessonOverlay) {
            window.showLessonOverlay(response.lesson);
          }

          // Highlight the word path temporarily for visual feedback
          if (response.path && window.highlightWordPath) {
            // Brief delay to show the permanent highlight first, then temporary path highlight
            setTimeout(() => {
              window.highlightWordPath(response.path);
            }, 500);
          }

          // Show success message
          if (window.showToast) {
            window.showToast(`Word revealed (−${this.revealCost})`);
          }

        } else {
          throw new Error(response.error || 'Failed to reveal word');
        }

        // Handle errors within safeAction scope
        if (!response.ok) {
          if (response.error && response.error.includes('INSUFFICIENT_CREDITS')) {
            this.handleInsufficientCredits();
          } else if (response.error && (response.error.includes('401') || response.error.includes('not authenticated'))) {
            console.log('User not authenticated, reveal functionality unavailable');
            alert('Please log in to use the reveal feature.');
          } else {
            alert(`Failed to reveal word: ${response.error || 'Unknown error'}`);
          }
        }
      });
    }

    // Fallback safe action if window.safeAction is not available
    async fallbackSafeAction(btn, fn) {
      if (btn.disabled) return;
      btn.disabled = true;
      const originalText = btn.textContent;
      try {
        await fn();
      } catch (error) {
        console.error('Reveal action error:', error);
        alert(`Error: ${error.message}`);
      } finally {
        btn.disabled = false;
        if (!btn.textContent.includes('Sign in')) {
          btn.textContent = originalText;
        }
      }
    }

    handleInsufficientCredits() {
      alert(`You need ${this.revealCost} credits to reveal a word. Visit the Store to buy more credits.`);

      if (window.openStoreModal) {
        window.openStoreModal();
      }
    }

    createRevealButton(puzzleId, wordId, wordText = '') {
      const button = document.createElement('button');
      button.className = 'btn reveal-btn';
      button.dataset.action = 'reveal';
      button.dataset.puzzleId = puzzleId;
      button.dataset.wordId = wordId;
      button.innerHTML = `Reveal ${wordText} (<span class="cost">${this.revealCost}</span>)`;

      return button;
    }
  }

  // Initialize everything when DOM is ready
  function initializeCreditsSystem() {
    // Check if user is logged in
    const isLoggedIn = document.querySelector('#credit-badge, #wallet') !== null ||
                      document.body.dataset.loggedIn === 'true';

    if (!isLoggedIn) {
      console.log('Credits system: User not logged in, skipping initialization');
      return;
    }

    // Initialize managers
    const creditsManager = new CreditsManager();
    const gameManager = new GameManager(creditsManager);
    const revealManager = new RevealManager(creditsManager);

    // Initialize all systems
    creditsManager.init();
    gameManager.init();
    revealManager.init();

    // Make managers globally available
    window.creditsSystem = {
      credits: creditsManager,
      game: gameManager,
      reveal: revealManager
    };

    console.log('Credits system initialized successfully');
  }

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeCreditsSystem);
  } else {
    initializeCreditsSystem();
  }

})();