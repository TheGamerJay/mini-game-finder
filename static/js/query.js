// Data-Attribute Contract ("no magic IDs")
// Address elements by stable data contracts instead of fragile IDs

(function() {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  function data(attr, value = null, root = document) {
    const selector = value === null
      ? `[data-${attr}]`
      : `[data-${attr}="${value}"]`;

    return $(selector, root);
  }

  function dataAll(attr, value = null, root = document) {
    const selector = value === null
      ? `[data-${attr}]`
      : `[data-${attr}="${value}"]`;

    return $$(selector, root);
  }

  function action(actionName, root = document) {
    return $(`[data-action="${actionName}"]`, root);
  }

  function actionAll(actionName, root = document) {
    return $$(`[data-action="${actionName}"]`, root);
  }

  function role(roleName, root = document) {
    return $(`[data-role="${roleName}"]`, root);
  }

  function roleAll(roleName, root = document) {
    return $$(`[data-role="${roleName}"]`, root);
  }

  function panel(panelName, root = document) {
    return $(`[data-panel="${panelName}"]`, root);
  }

  function panelAll(panelName, root = document) {
    return $$(`[data-panel="${panelName}"]`, root);
  }

  function component(componentName, root = document) {
    return $(`[data-component="${componentName}"]`, root);
  }

  function componentAll(componentName, root = document) {
    return $$(`[data-component="${componentName}"]`, root);
  }

  function state(stateName, stateValue = null, root = document) {
    const selector = stateValue === null
      ? `[data-state*="${stateName}"]`
      : `[data-state~="${stateName}:${stateValue}"]`;

    return $(selector, root);
  }

  function stateAll(stateName, stateValue = null, root = document) {
    const selector = stateValue === null
      ? `[data-state*="${stateName}"]`
      : `[data-state~="${stateName}:${stateValue}"]`;

    return $$(selector, root);
  }

  function closest(element, selector) {
    return element.closest(selector);
  }

  function parent(element, selector = null) {
    const parentEl = element.parentElement;
    if (!selector) return parentEl;
    return parentEl && parentEl.matches(selector) ? parentEl : null;
  }

  function children(element, selector = null) {
    const childElements = [...element.children];
    return selector ? childElements.filter(el => el.matches(selector)) : childElements;
  }

  function siblings(element, selector = null) {
    const siblingElements = [...element.parentElement.children].filter(el => el !== element);
    return selector ? siblingElements.filter(el => el.matches(selector)) : siblingElements;
  }

  function find(element, selector) {
    return $(selector, element);
  }

  function findAll(element, selector) {
    return $$(selector, element);
  }

  function matches(element, selector) {
    return element.matches(selector);
  }

  function contains(parent, child) {
    return parent.contains(child);
  }

  function createQuery(root) {
    return {
      $: (sel) => $(sel, root),
      $$: (sel) => $$(sel, root),
      data: (attr, value) => data(attr, value, root),
      dataAll: (attr, value) => dataAll(attr, value, root),
      action: (name) => action(name, root),
      actionAll: (name) => actionAll(name, root),
      role: (name) => role(name, root),
      roleAll: (name) => roleAll(name, root),
      panel: (name) => panel(name, root),
      panelAll: (name) => panelAll(name, root),
      component: (name) => component(name, root),
      componentAll: (name) => componentAll(name, root),
      state: (name, value) => state(name, value, root),
      stateAll: (name, value) => stateAll(name, value, root)
    };
  }

  // State management helpers
  function setState(element, stateName, stateValue) {
    const currentState = element.dataset.state || '';
    const states = currentState.split(' ').filter(s => s && !s.startsWith(`${stateName}:`));

    if (stateValue !== null && stateValue !== undefined) {
      states.push(`${stateName}:${stateValue}`);
    }

    element.dataset.state = states.join(' ');
  }

  function getState(element, stateName) {
    const currentState = element.dataset.state || '';
    const stateMatch = currentState.split(' ').find(s => s.startsWith(`${stateName}:`));
    return stateMatch ? stateMatch.split(':')[1] : null;
  }

  function hasState(element, stateName, stateValue = null) {
    const current = getState(element, stateName);
    return stateValue === null ? current !== null : current === stateValue;
  }

  function removeState(element, stateName) {
    const currentState = element.dataset.state || '';
    const states = currentState.split(' ').filter(s => s && !s.startsWith(`${stateName}:`));
    element.dataset.state = states.join(' ');
  }

  // Expose utilities globally
  window.Query = {
    $,
    $$,
    data,
    dataAll,
    action,
    actionAll,
    role,
    roleAll,
    panel,
    panelAll,
    component,
    componentAll,
    state,
    stateAll,
    closest,
    parent,
    children,
    siblings,
    find,
    findAll,
    matches,
    contains,
    createQuery,
    setState,
    getState,
    hasState,
    removeState
  };

  // Global shortcuts
  window.$ = $;
  window.$$ = $$;

})();