/**
 * Auto-save forms to localStorage (IHE-ERP v2.5.1)
 *
 * Automatically saves form field values to localStorage when the user types,
 * restoring them on page load if a draft exists.
 *
 * Features:
 * - Debounced save (500ms after last change)
 * - Per-form draft storage keyed by form id/name or page URL
 * - Restore banner notification when draft is found
 * - Clears draft on successful form submission
 * - Ignores password fields and hidden inputs
 *
 * Usage:
 *   <form id="eventForm" data-auto-save="true">...</form>
 *
 * Or include auto-save on ALL forms by setting AUTO_SAVE_ALL = true below.
 */
(function () {
    'use strict';

    var AUTO_SAVE_ALL = false;          // set true to auto-save every form
    var DEBOUNCE_MS = 500;
    var STORAGE_PREFIX = 'ihe_draft_';

    function getStorageKey(form) {
        var key = form.getAttribute('data-draft-key');
        if (key) return STORAGE_PREFIX + key;
        if (form.id) return STORAGE_PREFIX + form.id;
        if (form.name) return STORAGE_PREFIX + form.name;
        return STORAGE_PREFIX + window.location.pathname.replace(/\//g, '_');
    }

    function shouldSaveForm(form) {
        if (form.getAttribute('data-auto-save') === 'false') return false;
        if (form.getAttribute('data-auto-save') === 'true') return true;
        if (AUTO_SAVE_ALL) return true;
        return false;
    }

    function getFormData(form) {
        var data = {};
        for (var i = 0; i < form.elements.length; i++) {
            var el = form.elements[i];
            if (!el.name) continue;
            if (el.type === 'password' || el.type === 'hidden' || el.type === 'file') continue;
            if (el.disabled) continue;
            if (el.type === 'radio' || el.type === 'checkbox') {
                if (el.checked) data[el.name] = el.value;
                continue;
            }
            if (el.tagName === 'SELECT' && el.multiple) {
                var vals = [];
                for (var j = 0; j < el.options.length; j++) {
                    if (el.options[j].selected) vals.push(el.options[j].value);
                }
                data[el.name] = vals;
                continue;
            }
            data[el.name] = el.value;
        }
        return data;
    }

    function restoreFormData(form, data) {
        if (!data || typeof data !== 'object') return false;
        var restored = false;
        for (var key in data) {
            if (!Object.prototype.hasOwnProperty.call(data, key)) continue;
            var el = form.elements[key];
            if (!el) continue;
            if (el.type === 'password' || el.type === 'hidden' || el.type === 'file') continue;
            if (el.type === 'radio') {
                var radios = form.querySelectorAll('input[name="' + key + '"]');
                for (var i = 0; i < radios.length; i++) {
                    if (radios[i].value === data[key]) {
                        radios[i].checked = true;
                        restored = true;
                    }
                }
                continue;
            }
            if (el.type === 'checkbox') {
                el.checked = !!data[key];
                restored = true;
                continue;
            }
            if (el.tagName === 'SELECT' && el.multiple) {
                var vals = data[key];
                if (Array.isArray(vals)) {
                    for (var j = 0; j < el.options.length; j++) {
                        el.options[j].selected = vals.indexOf(el.options[j].value) !== -1;
                    }
                    restored = true;
                }
                continue;
            }
            el.value = data[key];
            restored = true;
        }
        return restored;
    }

    function showRestoreBanner(form, key) {
        var existing = document.querySelector('.ihe-draft-banner');
        if (existing) existing.remove();

        var banner = document.createElement('div');
        banner.className = 'ihe-draft-banner';
        banner.style.cssText = 'background:#fff3cd;border:1px solid #ffc107;border-radius:4px;padding:8px 12px;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between;font-size:13px;';
        banner.innerHTML = '<span>\u23F0 Saved draft found. <a href="#" class="ihe-draft-restore" style="color:#856404;font-weight:600;">Restore</a> or <a href="#" class="ihe-draft-discard" style="color:#856404;font-weight:600;">discard</a></span>';

        var restoreBtn = banner.querySelector('.ihe-draft-restore');
        var discardBtn = banner.querySelector('.ihe-draft-discard');

        restoreBtn.addEventListener('click', function (e) {
            e.preventDefault();
            try {
                var saved = JSON.parse(localStorage.getItem(key));
                if (saved && saved.data) {
                    restoreFormData(form, saved.data);
                }
            } catch (_) {}
            banner.remove();
        });

        discardBtn.addEventListener('click', function (e) {
            e.preventDefault();
            localStorage.removeItem(key);
            banner.remove();
        });

        if (form.parentNode) {
            form.parentNode.insertBefore(banner, form);
        }
    }

    function clearDraft(form) {
        var key = getStorageKey(form);
        localStorage.removeItem(key);
    }

    function saveDraft(form) {
        var key = getStorageKey(form);
        var data = getFormData(form);
        try {
            localStorage.setItem(key, JSON.stringify({
                data: data,
                savedAt: new Date().toISOString(),
                url: window.location.href
            }));
        } catch (_) {}
    }

    // Debounce helper
    function debounce(fn, ms) {
        var timer = null;
        return function () {
            var args = arguments;
            var ctx = this;
            if (timer) clearTimeout(timer);
            timer = setTimeout(function () {
                fn.apply(ctx, args);
                timer = null;
            }, ms);
        };
    }

    function init() {
        var forms = document.querySelectorAll('form');
        for (var i = 0; i < forms.length; i++) {
            var form = forms[i];
            if (!shouldSaveForm(form)) continue;

            var key = getStorageKey(form);

            // Check for existing draft
            try {
                var saved = JSON.parse(localStorage.getItem(key));
                if (saved && saved.data && Object.keys(saved.data).length > 0) {
                    // Auto-restore if less than 4 hours old; otherwise show banner
                    var age = Date.now() - new Date(saved.savedAt).getTime();
                    if (age < 4 * 60 * 60 * 1000) {
                        restoreFormData(form, saved.data);
                    } else {
                        showRestoreBanner(form, key);
                    }
                }
            } catch (_) {}

            // Debounced save on input
            var debouncedSave = debounce(function () {
                saveDraft(form);
            }, DEBOUNCE_MS);

            form.addEventListener('input', debouncedSave);
            form.addEventListener('change', debouncedSave);

            // Clear draft on successful submit
            form.addEventListener('submit', function () {
                // Delay clearing to allow the submit to proceed
                setTimeout(function () { clearDraft(form); }, 100);
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
