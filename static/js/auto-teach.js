// 🧠 Block E — Auto-Teach System
// Automatically shows word lessons when words are discovered, with user preferences

(function() {
  'use strict';

  class AutoTeachSystem {
    constructor() {
      this.enabled = true;
      this.preferences = {
        auto_teach_no_timer: true,  // Auto-teach in no-timer mode
        auto_teach_timer: false,    // Auto-teach in timer mode
        speak_enabled: true,        // TTS enabled
        lesson_auto_close: false    // Auto-close lesson overlays
      };
      this.currentGameMode = null;
      this.hasTimer = false;
      this.wordsQueue = [];
      this.isProcessing = false;
      this.loadPreferences();
    }

    async loadPreferences() {
      try {
        // Try to load from preferences API if available
        if (window.creditsSystem && window.creditsSystem.preferences) {
          const prefs = await this.fetchPreferences();
          this.preferences = { ...this.preferences, ...prefs };
        } else {
          // Fallback to localStorage
          this.loadFromLocalStorage();
        }
      } catch (error) {
        console.warn('Failed to load auto-teach preferences, using defaults:', error);
        this.loadFromLocalStorage();
      }

      console.log('Auto-teach preferences loaded:', this.preferences);
    }

    async fetchPreferences() {
      try {
        const response = await fetch('/api/prefs/get', {
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        return data.preferences || {};
      } catch (error) {
        console.warn('API preferences fetch failed:', error);
        return {};
      }
    }

    loadFromLocalStorage() {
      try {
        const saved = localStorage.getItem('mwf_auto_teach_prefs');
        if (saved) {
          const parsed = JSON.parse(saved);
          this.preferences = { ...this.preferences, ...parsed };
        }
      } catch (error) {
        console.warn('Failed to load preferences from localStorage:', error);
      }
    }

    async savePreferences() {
      try {
        // Try to save to preferences API
        if (window.creditsSystem && window.creditsSystem.preferences) {
          await this.saveToAPI();
        }

        // Always save to localStorage as backup
        this.saveToLocalStorage();
      } catch (error) {
        console.warn('Failed to save auto-teach preferences:', error);
        this.saveToLocalStorage();
      }
    }

    async saveToAPI() {
      const promises = Object.entries(this.preferences).map(([key, value]) =>
        fetch('/api/prefs/set', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key, value })
        })
      );

      await Promise.all(promises);
    }

    saveToLocalStorage() {
      try {
        localStorage.setItem('mwf_auto_teach_prefs', JSON.stringify(this.preferences));
      } catch (error) {
        console.warn('Failed to save preferences to localStorage:', error);
      }
    }

    setGameContext(mode, hasTimer) {
      this.currentGameMode = mode;
      this.hasTimer = hasTimer;

      console.log(`Auto-teach context: mode=${mode}, hasTimer=${hasTimer}`);
    }

    shouldAutoTeach() {
      if (!this.enabled) return false;

      // Check user preferences based on game mode
      if (this.hasTimer) {
        return this.preferences.auto_teach_timer;
      } else {
        return this.preferences.auto_teach_no_timer;
      }
    }

    async onWordFound(word, definition = null, example = null) {
      if (!this.shouldAutoTeach()) {
        console.log(`Auto-teach disabled for ${this.hasTimer ? 'timer' : 'no-timer'} mode`);
        return;
      }

      // Get word lesson data
      const lessonData = await this.getWordLesson(word, definition, example);

      if (!lessonData) {
        console.warn(`No lesson data available for word: ${word}`);
        return;
      }

      // Add to queue for processing
      this.wordsQueue.push({
        word: word,
        lesson: lessonData,
        timestamp: Date.now()
      });

      // Process queue
      this.processQueue();
    }

    async getWordLesson(word, definition = null, example = null) {
      // If we already have definition and example, use them
      if (definition) {
        return {
          word: word,
          definition: definition,
          example: example || this.generateExample(word)
        };
      }

      // Try to fetch from API
      try {
        const response = await fetch(`/api/word/lesson?word=${encodeURIComponent(word)}`, {
          credentials: 'include'
        });

        if (response.ok) {
          const data = await response.json();
          return data.lesson;
        }
      } catch (error) {
        console.warn('Failed to fetch word lesson from API:', error);
      }

      // Fallback to basic lesson data
      return {
        word: word,
        definition: this.getBasicDefinition(word),
        example: this.generateExample(word)
      };
    }

    getBasicDefinition(word) {
      // Simple fallback definitions for common words
      const basicDefinitions = {
        'cat': 'A small domesticated carnivorous mammal with soft fur.',
        'dog': 'A domesticated carnivorous mammal that typically has a long snout.',
        'house': 'A building for human habitation.',
        'car': 'A road vehicle, typically with four wheels.',
        'tree': 'A woody perennial plant with a trunk and branches.',
        'book': 'A written or printed work consisting of pages.',
        'water': 'A colorless, transparent, odorless liquid.',
        'fire': 'Combustion or burning, in which substances combine chemically with oxygen.',
        'sun': 'The star around which the earth orbits.',
        'moon': 'The natural satellite of the earth.'
      };

      return basicDefinitions[word.toLowerCase()] ||
             `A word that appears in word search puzzles. Look it up to learn more!`;
    }

    generateExample(word) {
      // Generate simple example sentences
      const templates = [
        `I can see a ${word} in the distance.`,
        `The ${word} is very important.`,
        `Have you ever seen a ${word} before?`,
        `This ${word} is really interesting.`,
        `I learned about ${word} today.`
      ];

      return templates[Math.floor(Math.random() * templates.length)];
    }

    async processQueue() {
      if (this.isProcessing || this.wordsQueue.length === 0) {
        return;
      }

      this.isProcessing = true;

      try {
        while (this.wordsQueue.length > 0) {
          const wordData = this.wordsQueue.shift();

          // Show lesson overlay
          if (window.showLessonOverlay) {
            window.showLessonOverlay(wordData.lesson);
          }

          // Wait for user to close lesson or auto-close timer
          await this.waitForLessonClose();

          // Small delay between lessons to avoid overwhelming
          if (this.wordsQueue.length > 0) {
            await this.delay(1000);
          }
        }
      } catch (error) {
        console.error('Error processing auto-teach queue:', error);
      } finally {
        this.isProcessing = false;
      }
    }

    async waitForLessonClose() {
      return new Promise((resolve) => {
        let timeout;

        const checkClosed = () => {
          if (!window.lessonOverlay || !window.lessonOverlay.isOpen) {
            clearTimeout(timeout);
            resolve();
            return;
          }
          timeout = setTimeout(checkClosed, 100);
        };

        // Auto-resolve after maximum wait time (30 seconds)
        setTimeout(() => {
          clearTimeout(timeout);
          resolve();
        }, 30000);

        checkClosed();
      });
    }

    delay(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Preference management methods
    setPreference(key, value) {
      if (this.preferences.hasOwnProperty(key)) {
        this.preferences[key] = value;
        this.savePreferences();
        console.log(`Auto-teach preference updated: ${key} = ${value}`);
      } else {
        console.warn(`Unknown auto-teach preference: ${key}`);
      }
    }

    getPreference(key) {
      return this.preferences[key];
    }

    toggleAutoTeach(mode) {
      if (mode === 'timer') {
        this.setPreference('auto_teach_timer', !this.preferences.auto_teach_timer);
      } else {
        this.setPreference('auto_teach_no_timer', !this.preferences.auto_teach_no_timer);
      }
    }

    enable() {
      this.enabled = true;
      console.log('Auto-teach system enabled');
    }

    disable() {
      this.enabled = false;
      this.wordsQueue = [];
      console.log('Auto-teach system disabled');
    }

    // Settings UI helper
    createSettingsPanel() {
      const panel = document.createElement('div');
      panel.className = 'auto-teach-settings';
      panel.innerHTML = `
        <h3>Auto-Teach Settings</h3>
        <label>
          <input type="checkbox" id="auto-teach-no-timer" ${this.preferences.auto_teach_no_timer ? 'checked' : ''}>
          Enable auto-teach in relaxed mode (no timer)
        </label>
        <label>
          <input type="checkbox" id="auto-teach-timer" ${this.preferences.auto_teach_timer ? 'checked' : ''}>
          Enable auto-teach in timed mode
        </label>
        <label>
          <input type="checkbox" id="speak-enabled" ${this.preferences.speak_enabled ? 'checked' : ''}>
          Enable text-to-speech pronunciation
        </label>
        <label>
          <input type="checkbox" id="lesson-auto-close" ${this.preferences.lesson_auto_close ? 'checked' : ''}>
          Auto-close lesson overlays after 5 seconds
        </label>
      `;

      // Bind events
      panel.querySelector('#auto-teach-no-timer').addEventListener('change', (e) => {
        this.setPreference('auto_teach_no_timer', e.target.checked);
      });

      panel.querySelector('#auto-teach-timer').addEventListener('change', (e) => {
        this.setPreference('auto_teach_timer', e.target.checked);
      });

      panel.querySelector('#speak-enabled').addEventListener('change', (e) => {
        this.setPreference('speak_enabled', e.target.checked);
      });

      panel.querySelector('#lesson-auto-close').addEventListener('change', (e) => {
        this.setPreference('lesson_auto_close', e.target.checked);
      });

      return panel;
    }

    // Integration with game detection
    setupGameIntegration() {
      // Listen for word found events
      document.addEventListener('wordFound', (event) => {
        const { word, definition, example } = event.detail;
        this.onWordFound(word, definition, example);
      });

      // Detect game mode from page
      const meta = document.getElementById('meta');
      if (meta) {
        const mode = meta.dataset.mode || 'easy';
        const hasTimer = meta.dataset.timer === '1' ||
                        meta.querySelector('[data-timer="1"]') !== null;
        this.setGameContext(mode, hasTimer);
      }
    }
  }

  // Initialize auto-teach system
  function initializeAutoTeach() {
    const autoTeach = new AutoTeachSystem();

    // Make it globally available
    window.autoTeachSystem = autoTeach;

    // Set up game integration
    autoTeach.setupGameIntegration();

    // Integration with existing word found detection
    if (window.markFound) {
      const originalMarkFound = window.markFound;
      window.markFound = function(word) {
        // Call original function
        originalMarkFound.call(this, word);

        // Trigger auto-teach
        autoTeach.onWordFound(word);
      };
    }

    console.log('Auto-teach system initialized');
  }

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAutoTeach);
  } else {
    initializeAutoTeach();
  }

})();