// 🎓 Block D — Lesson Overlay with TTS Pronunciation
// Interactive word lessons with browser text-to-speech integration

(function() {
  'use strict';

  class LessonOverlay {
    constructor() {
      this.isOpen = false;
      this.currentLesson = null;
      this.overlay = null;
      this.ttsSupported = 'speechSynthesis' in window;
      this.voices = [];
      this.preferredVoice = null;
      this.loadVoices();
    }

    loadVoices() {
      if (!this.ttsSupported) return;

      const updateVoices = () => {
        this.voices = speechSynthesis.getVoices();
        // Prefer English voices
        this.preferredVoice = this.voices.find(voice =>
          voice.lang.startsWith('en') && voice.default
        ) || this.voices.find(voice =>
          voice.lang.startsWith('en')
        ) || this.voices[0];
      };

      updateVoices();

      // Some browsers load voices asynchronously
      if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = updateVoices;
      }
    }

    createOverlay() {
      if (this.overlay) return this.overlay;

      this.overlay = document.createElement('div');
      this.overlay.className = 'lesson-overlay';
      this.overlay.innerHTML = `
        <div class="lesson-backdrop"></div>
        <div class="lesson-modal">
          <div class="lesson-header">
            <h2 class="lesson-title">Word Lesson</h2>
            <button class="lesson-close" aria-label="Close lesson">&times;</button>
          </div>
          <div class="lesson-content">
            <div class="lesson-word-section">
              <div class="lesson-word"></div>
              <button class="lesson-pronounce" title="Pronounce word">
                <span class="pronounce-icon">🔊</span>
                <span class="pronounce-text">Pronounce</span>
              </button>
            </div>
            <div class="lesson-definition-section">
              <h3>Definition</h3>
              <div class="lesson-definition"></div>
            </div>
            <div class="lesson-example-section">
              <h3>Example</h3>
              <div class="lesson-example"></div>
            </div>
            <div class="lesson-actions">
              <button class="lesson-practice">Practice Again</button>
              <button class="lesson-continue">Continue Playing</button>
            </div>
          </div>
        </div>
      `;

      // Add styles
      this.addStyles();

      // Bind events
      this.bindEvents();

      document.body.appendChild(this.overlay);
      return this.overlay;
    }

    addStyles() {
      if (document.getElementById('lesson-overlay-styles')) return;

      const styles = document.createElement('style');
      styles.id = 'lesson-overlay-styles';
      styles.textContent = `
        .lesson-overlay {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          z-index: 10000;
          display: none;
        }

        .lesson-backdrop {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.8);
          backdrop-filter: blur(4px);
        }

        .lesson-modal {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: #1f2937;
          border-radius: 16px;
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
          min-width: 400px;
          max-width: 600px;
          max-height: 80vh;
          overflow: hidden;
          border: 1px solid #374151;
        }

        .lesson-header {
          background: linear-gradient(135deg, #3b82f6, #1d4ed8);
          padding: 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          color: white;
        }

        .lesson-title {
          margin: 0;
          font-size: 24px;
          font-weight: 600;
        }

        .lesson-close {
          background: none;
          border: none;
          color: white;
          font-size: 32px;
          cursor: pointer;
          padding: 0;
          width: 40px;
          height: 40px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
        }

        .lesson-close:hover {
          background: rgba(255, 255, 255, 0.2);
          transform: scale(1.1);
        }

        .lesson-content {
          padding: 30px;
          color: #f3f4f6;
        }

        .lesson-word-section {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 30px;
          padding: 20px;
          background: #374151;
          border-radius: 12px;
          border: 1px solid #4b5563;
        }

        .lesson-word {
          font-size: 36px;
          font-weight: 700;
          color: #60a5fa;
          text-transform: uppercase;
          letter-spacing: 2px;
        }

        .lesson-pronounce {
          background: #3b82f6;
          border: none;
          color: white;
          padding: 12px 20px;
          border-radius: 8px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 16px;
          font-weight: 500;
          transition: all 0.2s ease;
        }

        .lesson-pronounce:hover {
          background: #2563eb;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }

        .lesson-pronounce:active {
          transform: translateY(0);
        }

        .lesson-pronounce.speaking {
          background: #10b981;
          animation: pulse 1s infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }

        .lesson-definition-section,
        .lesson-example-section {
          margin-bottom: 25px;
        }

        .lesson-definition-section h3,
        .lesson-example-section h3 {
          margin: 0 0 10px 0;
          font-size: 18px;
          font-weight: 600;
          color: #9ca3af;
        }

        .lesson-definition,
        .lesson-example {
          font-size: 16px;
          line-height: 1.6;
          color: #e5e7eb;
          background: #374151;
          padding: 15px;
          border-radius: 8px;
          border-left: 4px solid #3b82f6;
        }

        .lesson-example {
          font-style: italic;
          border-left-color: #10b981;
        }

        .lesson-actions {
          display: flex;
          gap: 15px;
          justify-content: flex-end;
          margin-top: 30px;
          padding-top: 20px;
          border-top: 1px solid #4b5563;
        }

        .lesson-practice,
        .lesson-continue {
          padding: 12px 24px;
          border: none;
          border-radius: 8px;
          font-size: 16px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .lesson-practice {
          background: #6b7280;
          color: white;
        }

        .lesson-practice:hover {
          background: #4b5563;
          transform: translateY(-1px);
        }

        .lesson-continue {
          background: #10b981;
          color: white;
        }

        .lesson-continue:hover {
          background: #059669;
          transform: translateY(-1px);
        }

        /* Mobile responsive */
        @media (max-width: 500px) {
          .lesson-modal {
            min-width: 90vw;
            margin: 20px;
          }

          .lesson-word {
            font-size: 28px;
          }

          .lesson-word-section {
            flex-direction: column;
            gap: 15px;
            text-align: center;
          }

          .lesson-actions {
            flex-direction: column;
          }
        }

        /* Animation classes */
        .lesson-overlay.show {
          display: block;
          animation: fadeIn 0.3s ease;
        }

        .lesson-overlay.hide {
          animation: fadeOut 0.3s ease;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        @keyframes fadeOut {
          from {
            opacity: 1;
          }
          to {
            opacity: 0;
          }
        }

        .lesson-modal.show {
          animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
          from {
            transform: translate(-50%, -60%);
            opacity: 0;
          }
          to {
            transform: translate(-50%, -50%);
            opacity: 1;
          }
        }
      `;

      document.head.appendChild(styles);
    }

    bindEvents() {
      const overlay = this.overlay;

      // Close button
      const closeBtn = overlay.querySelector('.lesson-close');
      closeBtn.addEventListener('click', () => this.hide());

      // Backdrop click to close
      const backdrop = overlay.querySelector('.lesson-backdrop');
      backdrop.addEventListener('click', () => this.hide());

      // Escape key to close
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.isOpen) {
          this.hide();
        }
      });

      // Pronounce button
      const pronounceBtn = overlay.querySelector('.lesson-pronounce');
      pronounceBtn.addEventListener('click', () => this.pronounceWord());

      // Action buttons
      const practiceBtn = overlay.querySelector('.lesson-practice');
      const continueBtn = overlay.querySelector('.lesson-continue');

      practiceBtn.addEventListener('click', () => {
        this.pronounceWord();
      });

      continueBtn.addEventListener('click', () => {
        this.hide();
      });
    }

    async pronounceWord() {
      if (!this.ttsSupported || !this.currentLesson) {
        console.warn('Text-to-speech not supported or no current lesson');
        return;
      }

      const word = this.currentLesson.word;
      const pronounceBtn = this.overlay.querySelector('.lesson-pronounce');

      try {
        // Cancel any current speech
        speechSynthesis.cancel();

        // Create utterance
        const utterance = new SpeechSynthesisUtterance(word);

        if (this.preferredVoice) {
          utterance.voice = this.preferredVoice;
        }

        utterance.rate = 0.8;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        // Visual feedback
        pronounceBtn.classList.add('speaking');
        pronounceBtn.querySelector('.pronounce-text').textContent = 'Speaking...';

        utterance.onend = () => {
          pronounceBtn.classList.remove('speaking');
          pronounceBtn.querySelector('.pronounce-text').textContent = 'Pronounce';
        };

        utterance.onerror = () => {
          pronounceBtn.classList.remove('speaking');
          pronounceBtn.querySelector('.pronounce-text').textContent = 'Pronounce';
          console.warn('Speech synthesis error');
        };

        speechSynthesis.speak(utterance);

      } catch (error) {
        console.error('Failed to pronounce word:', error);
        pronounceBtn.classList.remove('speaking');
        pronounceBtn.querySelector('.pronounce-text').textContent = 'Pronounce';
      }
    }

    show(lesson) {
      if (!lesson) {
        console.error('No lesson data provided');
        return;
      }

      this.currentLesson = lesson;
      this.createOverlay();

      // Populate content
      const wordEl = this.overlay.querySelector('.lesson-word');
      const definitionEl = this.overlay.querySelector('.lesson-definition');
      const exampleEl = this.overlay.querySelector('.lesson-example');
      const exampleSection = this.overlay.querySelector('.lesson-example-section');

      wordEl.textContent = lesson.word || 'Unknown';
      definitionEl.textContent = lesson.definition || 'No definition available.';

      if (lesson.example) {
        exampleEl.textContent = lesson.example;
        exampleSection.style.display = 'block';
      } else {
        exampleSection.style.display = 'none';
      }

      // Show with animation
      this.overlay.style.display = 'block';
      this.overlay.classList.add('show');
      this.overlay.querySelector('.lesson-modal').classList.add('show');

      this.isOpen = true;

      // Auto-pronounce on open if TTS is supported
      setTimeout(() => {
        if (this.isOpen) {
          this.pronounceWord();
        }
      }, 500);

      // Focus management for accessibility
      const closeBtn = this.overlay.querySelector('.lesson-close');
      closeBtn.focus();
    }

    hide() {
      if (!this.isOpen || !this.overlay) return;

      // Cancel any ongoing speech
      if (this.ttsSupported) {
        speechSynthesis.cancel();
      }

      this.overlay.classList.add('hide');

      setTimeout(() => {
        this.overlay.style.display = 'none';
        this.overlay.classList.remove('show', 'hide');
        this.overlay.querySelector('.lesson-modal').classList.remove('show');
        this.isOpen = false;
        this.currentLesson = null;
      }, 300);
    }

    // Auto-close feature based on user preferences
    setupAutoClose() {
      if (!this.isOpen) return;

      // Check user preference for auto-close
      if (window.creditsSystem && window.creditsSystem.preferences) {
        window.creditsSystem.preferences.get('lesson_auto_close').then(autoClose => {
          if (autoClose) {
            setTimeout(() => {
              if (this.isOpen) {
                this.hide();
              }
            }, 5000); // Auto-close after 5 seconds
          }
        }).catch(() => {
          // Default to no auto-close if preference loading fails
        });
      }
    }
  }

  // Initialize lesson overlay system
  function initializeLessonOverlay() {
    const lessonOverlay = new LessonOverlay();

    // Make it globally available
    window.showLessonOverlay = function(lesson) {
      lessonOverlay.show(lesson);
      lessonOverlay.setupAutoClose();
    };

    window.hideLessonOverlay = function() {
      lessonOverlay.hide();
    };

    // Integration with preferences system
    window.lessonOverlay = lessonOverlay;

    console.log('Lesson overlay system initialized');
  }

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeLessonOverlay);
  } else {
    initializeLessonOverlay();
  }

})();