/*
 * Enterprise school finder.
 *
 * Choose a province, search the DBE master list for your school, and get the
 * quintile and price without picking anything by hand. Shared by the pricing
 * dialog on /subscription and /subscription/redeem-package.
 *
 * No price is calculated here. Each search result arrives with the school type it
 * maps to, and the totals come from the existing quote endpoint
 * (/subscription/enterprise-pricing), which reads the pricing config. Changing a
 * price or PRICING_MODE therefore needs no change to this file.
 */
(function () {
  'use strict';

  var DEBOUNCE_MS = 300;
  var MIN_QUERY = 3;
  var MAX_RESULTS = 10;

  var NO_RESULTS_PROMPT =
    "Can't find your school? Select your school type manually";

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function SchoolFinder(root) {
    this.root = root;
    this.instance = root.getAttribute('data-sf-instance') || 'page';
    this.searchUrl = root.getAttribute('data-sf-search');
    this.quoteUrl = root.getAttribute('data-sf-quote');
    this.redeemUrl = root.getAttribute('data-sf-redeem');
    this.minimum = parseInt(root.getAttribute('data-sf-minimum'), 10) || 100;
    this.minChars = parseInt(root.getAttribute('data-sf-min-chars'), 10) || MIN_QUERY;

    this.province = root.querySelector('[data-sf-province]');
    this.query = root.querySelector('[data-sf-query]');
    this.suggestions = root.querySelector('[data-sf-suggestions]');
    this.status = root.querySelector('[data-sf-status]');
    this.learners = root.querySelector('[data-sf-learners]');

    this.selectedPanel = root.querySelector('[data-sf-selected]');
    this.selectedName = root.querySelector('[data-sf-selected-name]');
    this.selectedMeta = root.querySelector('[data-sf-selected-meta]');
    this.selectedNote = root.querySelector('[data-sf-selected-note]');
    this.selectedPrice = root.querySelector('[data-sf-selected-price]');

    this.manual = root.querySelector('[data-sf-manual]');
    this.manualToggle = root.querySelector('[data-sf-manual-toggle]');
    this.manualFields = root.querySelector('[data-sf-manual-fields]');
    this.manualType = root.querySelector('[data-sf-manual-type]');
    this.notSure = root.querySelector('[data-sf-not-sure]');

    this.totals = root.querySelector('[data-sf-totals]');
    this.totalMonth = root.querySelector('[data-sf-total-month]');
    this.totalYear = root.querySelector('[data-sf-total-year]');
    this.breakdown = root.querySelector('[data-sf-breakdown]');
    this.errorBox = root.querySelector('[data-sf-error]');

    this.school = null;
    this.schoolType = '';
    this.searchTimer = null;
    this.searchRequest = null;
    this.quoteRequest = null;
    this.activeIndex = -1;

    this.schoolNameInput = this.findSchoolNameInput();
    this.bind();
    this.applyPreselection();
  }

  /* On the redeem page the finder sits above a real "School name" field which it
     fills in. In the dialog there is no such field. */
  SchoolFinder.prototype.findSchoolNameInput = function () {
    if (this.root.getAttribute('data-sf-autofill-name') !== 'redeem') return null;
    return document.querySelector('[name="school_name"]');
  };

  SchoolFinder.prototype.bind = function () {
    var self = this;

    this.province.addEventListener('change', function () {
      self.reset();
      if (self.province.value) {
        self.query.disabled = false;
        self.query.placeholder =
          'Type at least ' + self.minChars + ' letters of your school name';
        self.setStatus('Now type your school name to search.');
        self.query.focus();
      } else {
        self.setStatus('Choose your province to begin.');
      }
    });

    this.query.addEventListener('input', function () {
      self.onQueryChanged();
    });

    this.query.addEventListener('keydown', function (event) {
      self.onQueryKeydown(event);
    });

    this.manualToggle.addEventListener('click', function () {
      var showing = !self.manualFields.hidden;
      self.manualFields.hidden = showing;
      self.manualToggle.setAttribute('aria-expanded', showing ? 'false' : 'true');
      if (!showing && self.manualType) self.manualType.focus();
    });

    this.manualType.addEventListener('change', function () {
      self.schoolType = self.manualType.value;
      self.refreshQuote();
    });

    this.notSure.addEventListener('change', function () {
      if (self.notSure.checked && self.manualType) {
        self.manualType.value = '';
        self.schoolType = '';
      }
      self.refreshQuote();
    });

    this.learners.addEventListener('input', function () {
      self.refreshQuote();
    });

    /* Clicking away from the combobox dismisses the suggestion list. */
    document.addEventListener('click', function (event) {
      if (!self.root.contains(event.target)) self.closeSuggestions();
    });
  };

  SchoolFinder.prototype.reset = function () {
    this.school = null;
    this.schoolType = '';
    this.closeSuggestions();
    this.selectedPanel.hidden = true;
    this.totals.hidden = true;
    this.errorBox.hidden = true;
    this.hideManual();
    this.learners.value = this.minimum;
    if (this.schoolNameInput) this.schoolNameInput.value = '';
    this.notifyActivation();
  };

  SchoolFinder.prototype.setStatus = function (message) {
    if (!message) {
      this.status.hidden = true;
      this.status.textContent = '';
      return;
    }
    this.status.textContent = message;
    this.status.hidden = false;
  };

  SchoolFinder.prototype.hideManual = function () {
    this.manual.hidden = true;
    this.manualFields.hidden = true;
    this.manualToggle.setAttribute('aria-expanded', 'false');
    if (this.notSure) this.notSure.checked = false;
    if (this.manualType) this.manualType.value = '';
  };

  SchoolFinder.prototype.showManualPrompt = function () {
    this.manual.hidden = false;
  };

  /* ---------------------------------------------------------------- search */

  SchoolFinder.prototype.onQueryChanged = function () {
    var self = this;
    var query = this.query.value.trim();

    this.closeSuggestions();

    if (query.length < this.minChars) {
      this.setStatus(
        query.length
          ? 'Keep typing — ' + this.minChars + ' letters needed.'
          : ''
      );
      return;
    }

    this.setStatus('Searching&hellip;');
    this.suggestions.innerHTML =
      '<li class="sf-suggestion sf-suggestion-status">Searching&hellip;</li>';
    this.suggestions.hidden = false;
    this.query.setAttribute('aria-expanded', 'true');

    if (this.searchTimer) window.clearTimeout(this.searchTimer);
    this.searchTimer = window.setTimeout(function () {
      self.runSearch(query);
    }, DEBOUNCE_MS);
  };

  SchoolFinder.prototype.runSearch = function (query) {
    var self = this;
    var url =
      this.searchUrl +
      '?province=' +
      encodeURIComponent(this.province.value) +
      '&q=' +
      encodeURIComponent(query);

    if (this.searchRequest) this.searchRequest.abort();
    var pending = new XMLHttpRequest();
    this.searchRequest = pending;
    pending.open('GET', url);
    pending.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    pending.onload = function () {
      if (pending !== self.searchRequest) return;
      self.searchRequest = null;
      if (pending.status !== 200) {
        self.closeSuggestions();
        self.setStatus('');
        return;
      }
      var payload;
      try {
        payload = JSON.parse(pending.responseText);
      } catch (error) {
        self.closeSuggestions();
        return;
      }
      self.renderSuggestions(payload.results || []);
    };
    pending.send();
  };

  SchoolFinder.prototype.renderSuggestions = function (results) {
    this.suggestions.innerHTML = '';
    this.activeIndex = -1;
    this.lastResults = results.slice(0, MAX_RESULTS);

    if (!this.lastResults.length) {
      var empty = el(
        'li',
        'sf-suggestion sf-suggestion-empty',
        'No matching school in this province.'
      );
      this.suggestions.appendChild(empty);
      this.suggestions.hidden = false;
      this.setStatus(NO_RESULTS_PROMPT);
      this.showManualPrompt();
      return;
    }

    var self = this;
    this.lastResults.forEach(function (school, index) {
      var item = el('li', 'sf-suggestion');
      item.setAttribute('role', 'option');
      item.setAttribute('id', 'sf-option-' + self.instance + '-' + index);
      item.setAttribute('aria-selected', 'false');
      item.setAttribute('data-sf-school-id', school.id);

      var name = el('span', 'sf-suggestion-name', school.name);
      item.appendChild(name);

      /* Town and district, so two schools with the same name can be told apart. */
      if (school.town || school.district) {
        var place = school.town || school.township_village;
        var label = place
          ? place + (school.district ? ' (' + school.district + ')' : '')
          : school.district;
        item.appendChild(el('span', 'sf-suggestion-place', label));
      }

      var detail = [];
      if (school.quintile) detail.push('Quintile ' + school.quintile);
      else if (school.sector === 'independent') detail.push('Independent');
      else detail.push('Quintile not on record');
      item.appendChild(el('span', 'sf-suggestion-quintile', detail.join(' \u00b7 ')));

      item.addEventListener('mousedown', function (event) {
        event.preventDefault();
        self.selectSchool(school);
      });
      item.addEventListener('mouseenter', function () {
        self.setActive(index);
      });

      self.suggestions.appendChild(item);
    });

    this.suggestions.hidden = false;
    this.query.setAttribute('aria-expanded', 'true');
    this.setStatus(
      this.lastResults.length === 1
        ? 'One match. Use the arrow keys and Enter to choose it.'
        : 'Use the arrow keys and Enter to choose your school.'
    );
  };

  SchoolFinder.prototype.setActive = function (index) {
    var items = this.suggestions.querySelectorAll('[role="option"]');
    if (!items.length) return;
    if (index < 0) index = items.length - 1;
    if (index >= items.length) index = 0;
    this.activeIndex = index;
    for (var i = 0; i < items.length; i += 1) {
      var isActive = i === index;
      items[i].setAttribute('aria-selected', isActive ? 'true' : 'false');
      items[i].classList.toggle('is-active', isActive);
    }
    items[index].scrollIntoView({ block: 'nearest' });
    this.query.setAttribute('aria-activedescendant', items[index].id);
  };

  SchoolFinder.prototype.onQueryKeydown = function (event) {
    var items = this.suggestions.querySelectorAll('[role="option"]');
    if (event.key === 'Escape') {
      if (!this.suggestions.hidden) {
        event.stopPropagation();
        this.closeSuggestions();
      }
      return;
    }
    if (!items.length || this.suggestions.hidden) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.setActive(this.activeIndex + 1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.setActive(this.activeIndex - 1);
    } else if (event.key === 'Enter') {
      if (this.activeIndex >= 0 && items[this.activeIndex]) {
        event.preventDefault();
        var school = this.lastResults[this.activeIndex];
        if (school) this.selectSchool(school);
      }
    }
  };

  SchoolFinder.prototype.closeSuggestions = function () {
    this.suggestions.innerHTML = '';
    this.suggestions.hidden = true;
    this.activeIndex = -1;
    this.query.setAttribute('aria-expanded', 'false');
    this.query.removeAttribute('aria-activedescendant');
  };

  /* -------------------------------------------------------------- selection */

  SchoolFinder.prototype.selectSchool = function (school) {
    this.school = school;
    this.query.value = school.name;
    this.closeSuggestions();
    this.setStatus('');

    this.selectedName.textContent = school.display_label;
    this.selectedMeta.textContent = this.describeSchool(school);
    this.selectedNote.textContent = school.quintile_note;
    this.selectedPrice.textContent = school.price_per_learner_month;
    this.selectedPanel.hidden = false;

    if (school.needs_manual_quintile) {
      /* Rule 3: a public school with no quintile on record. We do not guess, so
         ask for it. */
      this.schoolType = '';
      this.showManualPrompt();
      this.manualFields.hidden = false;
      this.manualToggle.setAttribute('aria-expanded', 'true');
      this.manualType.value = '';
    } else {
      this.hideManual();
      this.schoolType = school.price_school_type;
    }

    /* Published enrolment, never below the Enterprise minimum. */
    this.learners.value = school.prefilled_learners;
    if (this.schoolNameInput) this.schoolNameInput.value = school.name;

    this.refreshQuote();
    this.notifyActivation();
  };

  SchoolFinder.prototype.describeSchool = function (school) {
    var parts = [school.province];
    if (school.learners_2025) {
      parts.push(
        school.learners_2025.toLocaleString('en-ZA') +
          ' learners in 2025'
      );
    }
    if (school.school_type_label) parts.push(school.school_type_label);
    return parts.join(' \u00b7 ');
  };

  /* ---------------------------------------------------------------- pricing */

  SchoolFinder.prototype.refreshQuote = function () {
    var self = this;
    var learners = parseInt(this.learners.value, 10);

    if (!this.schoolType) {
      this.totals.hidden = true;
      this.errorBox.hidden = false;
      this.errorBox.textContent =
        'Choose your school type above to see the price for your school.';
      this.notifyActivation();
      return;
    }

    if (this.notSure && this.notSure.checked) {
      this.totals.hidden = true;
      this.errorBox.hidden = false;
      this.errorBox.textContent =
        'We will confirm the exact price for your school when you activate the package.';
      this.notifyActivation();
      return;
    }

    if (!learners || learners < this.minimum) {
      this.totals.hidden = true;
      this.errorBox.hidden = false;
      this.errorBox.textContent =
        'Enterprise packages start at ' +
        this.minimum +
        ' learners — please enter ' +
        this.minimum +
        ' or more.';
      this.notifyActivation();
      return;
    }

    if (this.quoteRequest) this.quoteRequest.abort();
    var url =
      this.quoteUrl +
      '?school_type=' +
      encodeURIComponent(this.schoolType) +
      '&learners=' +
      encodeURIComponent(learners);
    var pending = new XMLHttpRequest();
    this.quoteRequest = pending;
    pending.open('GET', url);
    pending.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    pending.onload = function () {
      if (pending !== self.quoteRequest) return;
      self.quoteRequest = null;
      if (pending.status !== 200) return;
      var quote;
      try {
        quote = JSON.parse(pending.responseText);
      } catch (error) {
        return;
      }
      if (!quote.valid) {
        self.totals.hidden = true;
        self.errorBox.hidden = false;
        self.errorBox.textContent = quote.error;
        return;
      }
      self.errorBox.hidden = true;
      self.totalMonth.textContent = quote.total_month;
      self.totalYear.textContent = quote.total_year;
      self.breakdown.textContent = quote.breakdown;
      self.totals.hidden = false;
    };
    pending.send();
  };

  /* --------------------------------------------------------- activation hand-off */

  SchoolFinder.prototype.activationParams = function () {
    if (!this.school && !this.schoolType) return null;
    var learners = parseInt(this.learners.value, 10);
    if (!learners || learners < this.minimum) learners = this.minimum;
    var params = ['learners=' + encodeURIComponent(learners)];
    if (this.school) {
      params.unshift('school_id=' + encodeURIComponent(this.school.id));
      params.unshift('school_name=' + encodeURIComponent(this.school.name));
    }
    if (this.schoolType) {
      params.push('school_type=' + encodeURIComponent(this.schoolType));
    }
    if (this.selectedPrice && this.selectedPrice.textContent) {
      params.push('price=' + encodeURIComponent(this.selectedPrice.textContent));
    }
    return params.join('&');
  };

  SchoolFinder.prototype.notifyActivation = function () {
    var link = this.root.querySelector('[data-sf-activate]');
    if (!link) return;
    var params = this.activationParams();
    link.setAttribute('href', params ? this.redeemUrl + '?' + params : this.redeemUrl);
  };

  /* --------------------------------------------------------- preselection */

  SchoolFinder.prototype.applyPreselection = function () {
    var payload = this.root.getAttribute('data-sf-preselect-json');
    if (!payload) return;
    var school;
    try {
      school = JSON.parse(payload);
    } catch (error) {
      return;
    }
    if (!school || !school.id) return;
    this.province.value = school.province;
    this.query.disabled = false;
    this.selectSchool(school);
    this.setStatus('');
  };

  function init() {
    var roots = document.querySelectorAll('[data-school-finder]');
    for (var i = 0; i < roots.length; i += 1) {
      new SchoolFinder(roots[i]);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.SGILASchoolFinder = SchoolFinder;
})();