// Consistent Form Handling (Single Source of Truth)
// Prevent partial state, double submits, and racey UX

(function() {
  'use strict';

  function handleForm(form, onSubmit, options = {}) {
    const {
      preventDefault = true,
      disableOnSubmit = true,
      resetOnSuccess = false,
      validateOnSubmit = null,
      showErrors = true
    } = options;

    let busy = false;

    const toggleFormState = (disabled) => {
      if (!disableOnSubmit) return;

      form.querySelectorAll("button, input, select, textarea").forEach(element => {
        if (element.type !== 'hidden') {
          element.disabled = disabled;
        }
      });

      form.classList.toggle('form-submitting', disabled);
    };

    const showFormError = (message) => {
      if (!showErrors) return;

      clearFormErrors();

      const errorEl = document.createElement('div');
      errorEl.className = 'form-error';
      errorEl.textContent = message;
      errorEl.style.cssText = `
        color: #dc3545;
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 4px;
        padding: 8px 12px;
        margin: 8px 0;
        font-size: 14px;
      `;

      form.insertBefore(errorEl, form.firstChild);
    };

    const clearFormErrors = () => {
      form.querySelectorAll('.form-error').forEach(el => el.remove());
    };

    const listener = async (e) => {
      if (preventDefault) {
        e.preventDefault();
      }

      if (busy) return;

      clearFormErrors();

      const formData = new FormData(form);
      const data = Object.fromEntries(formData);

      if (validateOnSubmit) {
        const validation = validateOnSubmit(data, form);
        if (validation !== true) {
          showFormError(validation || 'Form validation failed');
          return;
        }
      }

      busy = true;
      toggleFormState(true);

      try {
        const result = await onSubmit(data, form, formData);

        if (resetOnSuccess && result !== false) {
          form.reset();
        }

        return result;

      } catch (error) {
        console.error('Form submission error:', error);
        showFormError(error.message || 'Submission failed. Please try again.');
        throw error;

      } finally {
        busy = false;
        toggleFormState(false);
      }
    };

    form.addEventListener("submit", listener, { passive: false });

    return () => {
      form.removeEventListener("submit", listener);
      clearFormErrors();
    };
  }

  function createFormValidator(rules) {
    return function validate(data) {
      for (const [field, validators] of Object.entries(rules)) {
        const value = data[field];

        for (const validator of validators) {
          if (typeof validator === 'function') {
            const result = validator(value, data);
            if (result !== true) {
              return result || `${field} is invalid`;
            }
          } else if (typeof validator === 'object') {
            const { required, minLength, maxLength, pattern, custom } = validator;

            if (required && (!value || value.toString().trim() === '')) {
              return `${field} is required`;
            }

            if (value && minLength && value.length < minLength) {
              return `${field} must be at least ${minLength} characters`;
            }

            if (value && maxLength && value.length > maxLength) {
              return `${field} must be no more than ${maxLength} characters`;
            }

            if (value && pattern && !pattern.test(value)) {
              return `${field} format is invalid`;
            }

            if (custom) {
              const result = custom(value, data);
              if (result !== true) {
                return result || `${field} is invalid`;
              }
            }
          }
        }
      }

      return true;
    };
  }

  function autoSaveForm(form, saveHandler, options = {}) {
    const {
      debounceMs = 1000,
      saveOnBlur = true,
      saveOnChange = true,
      excludeFields = [],
      storageKey = null
    } = options;

    let saveTimeout;
    let lastSavedData = '';

    const getSaveData = () => {
      const formData = new FormData(form);
      const data = {};

      for (const [key, value] of formData.entries()) {
        if (!excludeFields.includes(key)) {
          data[key] = value;
        }
      }

      return data;
    };

    const save = async () => {
      const data = getSaveData();
      const dataStr = JSON.stringify(data);

      if (dataStr === lastSavedData) return;

      try {
        await saveHandler(data, form);
        lastSavedData = dataStr;

        if (storageKey) {
          localStorage.setItem(storageKey, dataStr);
        }

      } catch (error) {
        console.error('Auto-save error:', error);
      }
    };

    const debouncedSave = () => {
      clearTimeout(saveTimeout);
      saveTimeout = setTimeout(save, debounceMs);
    };

    if (saveOnChange) {
      form.addEventListener('input', debouncedSave);
      form.addEventListener('change', debouncedSave);
    }

    if (saveOnBlur) {
      form.addEventListener('focusout', save);
    }

    if (storageKey) {
      try {
        const saved = localStorage.getItem(storageKey);
        if (saved) {
          const data = JSON.parse(saved);
          Object.entries(data).forEach(([key, value]) => {
            const field = form.elements[key];
            if (field) {
              field.value = value;
            }
          });
        }
      } catch (e) {
        console.warn('Failed to restore form data:', e);
      }
    }

    return () => {
      clearTimeout(saveTimeout);
      form.removeEventListener('input', debouncedSave);
      form.removeEventListener('change', debouncedSave);
      form.removeEventListener('focusout', save);
    };
  }

  function fieldDependencies(form, dependencies) {
    const updateDependencies = () => {
      const formData = new FormData(form);
      const data = Object.fromEntries(formData);

      dependencies.forEach(({ trigger, target, condition, action }) => {
        const triggerField = form.elements[trigger];
        const targetField = form.elements[target];

        if (!triggerField || !targetField) return;

        const shouldApply = typeof condition === 'function'
          ? condition(data[trigger], data, triggerField)
          : data[trigger] === condition;

        if (action === 'show') {
          targetField.style.display = shouldApply ? '' : 'none';
          const label = form.querySelector(`label[for="${target}"]`);
          if (label) label.style.display = shouldApply ? '' : 'none';
        } else if (action === 'enable') {
          targetField.disabled = !shouldApply;
        } else if (action === 'require') {
          targetField.required = shouldApply;
        } else if (typeof action === 'function') {
          action(targetField, shouldApply, data);
        }
      });
    };

    form.addEventListener('input', updateDependencies);
    form.addEventListener('change', updateDependencies);

    updateDependencies();

    return () => {
      form.removeEventListener('input', updateDependencies);
      form.removeEventListener('change', updateDependencies);
    };
  }

  // Expose utilities
  window.Forms = {
    handleForm,
    createFormValidator,
    autoSaveForm,
    fieldDependencies
  };

})();