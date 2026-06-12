(function() {
  'use strict';

  class MetaLayer {
    constructor(formEl, config) {
      this.form = formEl;
      this.config = config;
      this.auditLog = [];
      this.draftKey = 'meta_draft_' + (config.form_name || 'unknown');
      this.init();
    }

    init() {
      this.bindAutoFill();
      this.bindFormulas();
      this.bindValidations();
      this.bindConditions();
      this.bindAutoSave();
      this.bindAudit();
      this.restoreDraft();
    }

    // Helpers
    getFieldValue(name) {
      const el = this.form.querySelector(`[name="${name}"]`);
      if (!el) return null;
      if (el.type === 'checkbox') return el.checked;
      if (el.type === 'number') return parseFloat(el.value) || 0;
      return el.value;
    }

    setFieldValue(name, value) {
      const el = this.form.querySelector(`[name="${name}"]`);
      if (!el) return;
      const oldVal = el.value;
      el.value = value;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return oldVal;
    }

    getAllValues() {
      const data = {};
      this.form.querySelectorAll('[name]').forEach(el => {
        if (el.type === 'checkbox') data[el.name] = el.checked;
        else if (el.type === 'number') data[el.name] = parseFloat(el.value) || 0;
        else data[el.name] = el.value;
      });
      return data;
    }

    showError(el, msg) {
      el.style.borderColor = msg ? 'var(--accent-red, #ef4444)' : '';
      let errEl = el.parentElement.querySelector('.meta-error');
      if (!errEl && msg) {
        errEl = document.createElement('div');
        errEl.className = 'meta-error';
        errEl.style.cssText = 'color:var(--accent-red,#ef4444);font-size:0.75rem;margin-top:2px;';
        el.parentElement.appendChild(errEl);
      }
      if (errEl) errEl.textContent = msg || '';
    }

    showToast(msg, type) {
      let toast = document.querySelector('.meta-toast');
      if (!toast) {
        toast = document.createElement('div');
        toast.className = 'meta-toast';
        toast.style.cssText = 'position:fixed;bottom:20px;right:20px;padding:8px 16px;background:#1e293b;color:#fff;border-radius:8px;font-size:0.8rem;z-index:9999;opacity:0;transition:opacity 0.3s;';
        document.body.appendChild(toast);
      }
      toast.textContent = msg;
      toast.style.background = type === 'error' ? '#ef4444' : type === 'success' ? '#22c55e' : '#1e293b';
      toast.style.opacity = '1';
      setTimeout(() => { toast.style.opacity = '0'; }, 3000);
    }

    // --- AUTO FILL ---
    bindAutoFill() {
      const rules = this.config.auto_fill || {};
      Object.entries(rules).forEach(([fieldName, rule]) => {
        const el = this.form.querySelector(`[name="${fieldName}"]`);
        if (!el) return;
        el.addEventListener(rule.trigger || 'change', async () => {
          const val = el.value;
          if (!val) return;
          const url = (rule.fetch || '').replace('{value}', encodeURIComponent(val));
          if (!url) return;
          try {
            const res = await fetch(url);
            const data = await res.json();
            Object.entries(rule.target_fields || {}).forEach(([target, source]) => {
              const sourceVal = typeof source === 'function' ? source(data) : data[source];
              if (sourceVal !== undefined) {
                this.setFieldValue(target, sourceVal);
                const targetEl = this.form.querySelector(`[name="${target}"]`);
                if (targetEl) {
                  targetEl.style.transition = 'background 0.5s';
                  targetEl.style.background = 'rgba(6,182,212,0.1)';
                  setTimeout(() => { targetEl.style.background = ''; }, 1500);
                }
              }
            });
          } catch (err) {
            console.warn('[MetaLayer] Auto-fill failed:', err);
          }
        });
      });
    }

    // --- FORMULAS ---
    bindFormulas() {
      const formulas = this.config.formulas || {};
      Object.entries(formulas).forEach(([targetField, formula]) => {
        const refs = formula.match(/[A-Za-z_]\w*/g) || [];
        refs.forEach(ref => {
          const el = this.form.querySelector(`[name="${ref}"]`);
          if (el) {
            const handler = () => {
              const vals = this.getAllValues();
              let expr = formula;
              Object.entries(vals).forEach(([k, v]) => {
                expr = expr.replace(new RegExp('\\b' + k + '\\b', 'g'), typeof v === 'number' ? v : `"${v}"`);
              });
              try {
                const result = new Function('"use strict"; return (' + expr + ')')();
                const targetEl = this.form.querySelector(`[name="${targetField}"]`);
                if (targetEl) {
                  const computed = isNaN(result) ? '' : Number(result).toFixed(2);
                  targetEl.value = computed;
                  targetEl.dispatchEvent(new Event('change', { bubbles: true }));
                  targetEl.style.background = 'rgba(16,185,129,0.1)';
                  targetEl.style.fontWeight = '600';
                }
              } catch (e) {
                // silent
              }
            };
            el.addEventListener('input', handler);
            el.addEventListener('change', handler);
          }
        });
      });
    }

    // --- VALIDATIONS ---
    bindValidations() {
      const validations = this.config.validations || {};
      Object.entries(validations).forEach(([fieldName, rules]) => {
        const el = this.form.querySelector(`[name="${fieldName}"]`);
        if (!el) return;
        const validate = async () => {
          let valid = true;
          let msg = '';
          const val = el.value;
          if (rules.required && !val) {
            valid = false; msg = 'This field is required';
          } else if (val) {
            if (rules.regex && !new RegExp(rules.regex).test(val)) {
              valid = false; msg = rules.message || 'Invalid format';
            }
            if (rules.min !== undefined && parseFloat(val) < rules.min) {
              valid = false; msg = `Minimum value is ${rules.min}`;
            }
            if (rules.max !== undefined && parseFloat(val) > rules.max) {
              valid = false; msg = `Maximum value is ${rules.max}`;
            }
            if (rules.unique && val) {
              try {
                const res = await fetch((rules.unique_endpoint || '/api/validate/unique') + '?' + new URLSearchParams({ field: fieldName, value: val }));
                const result = await res.json();
                if (!result.unique) {
                  valid = false; msg = rules.message || 'This value already exists';
                }
              } catch (e) { /* skip if server unavailable */ }
            }
          }
          this.showError(el, valid ? '' : msg);
          return valid;
        };
        el.addEventListener('blur', validate);
        if (rules.required) {
          el.required = true;
        }
      });
    }

    // --- CONDITIONAL DISPLAY ---
    bindConditions() {
      const conditions = this.config.conditions || {};
      Object.entries(conditions).forEach(([fieldName, rule]) => {
        const el = this.form.querySelector(`[name="${fieldName}"]`);
        if (!el) return;
        const wrapper = el.closest('.mb-3') || el.closest('.form-group') || el.parentElement;
        const check = () => {
          const vals = this.getAllValues();
          let expr = rule.show_when || 'true';
          Object.entries(vals).forEach(([k, v]) => {
            const strVal = typeof v === 'string' ? `"${v}"` : v;
            expr = expr.replace(new RegExp('\\b' + k + '\\b', 'g'), strVal);
          });
          try {
            const visible = new Function('"use strict"; return (' + expr + ')')();
            wrapper.style.display = visible ? '' : 'none';
            wrapper.style.maxHeight = visible ? '' : '0';
            wrapper.style.overflow = visible ? '' : 'hidden';
            wrapper.style.opacity = visible ? '1' : '0';
            wrapper.style.transition = 'all 0.3s';
          } catch (e) { /* silent */ }
        };
        this.form.querySelectorAll('[name]').forEach(inp => {
          inp.addEventListener('change', check);
          inp.addEventListener('input', check);
        });
        check();
      });
    }

    // --- AUTO-SAVE ---
    bindAutoSave() {
      const cfg = this.config.autosave || {};
      if (!cfg.enabled) return;
      const interval = (cfg.interval_seconds || 30) * 1000;
      this._saveTimer = setInterval(() => {
        const fd = new FormData(this.form);
        const data = {};
        fd.forEach((v, k) => { data[k] = v; });
        try {
          localStorage.setItem(this.draftKey, JSON.stringify(data));
          this.showToast('Draft auto-saved', 'success');
        } catch (e) { /* storage full */ }
      }, interval);
    }

    restoreDraft() {
      const cfg = this.config.autosave || {};
      if (!cfg.enabled) return;
      try {
        const draft = localStorage.getItem(this.draftKey);
        if (!draft) return;
        const data = JSON.parse(draft);
        Object.entries(data).forEach(([name, value]) => {
          const el = this.form.querySelector(`[name="${name}"]`);
          if (el && !el.value) el.value = value;
        });
        this.showToast('Draft restored', 'info');
      } catch (e) { /* ignore */ }
    }

    // --- AUDIT ---
    bindAudit() {
      const cfg = this.config.audit || {};
      if (!cfg.enabled) return;
      this.form.querySelectorAll('[name]').forEach(el => {
        el.dataset.oldValue = el.value;
        el.addEventListener('change', () => {
          this.auditLog.push({
            field: el.name,
            oldValue: el.dataset.oldValue,
            newValue: el.value,
            timestamp: new Date().toISOString(),
            user: document.body.dataset.user || 'anonymous'
          });
          el.dataset.oldValue = el.value;
        });
      });
      this.form.addEventListener('submit', () => {
        if (this.auditLog.length > 0) {
          const endpoint = this.config.audit.endpoint || '/api/meta/audit';
          try {
            navigator.sendBeacon(endpoint, JSON.stringify({
              form: this.config.form_name,
              page: window.location.pathname,
              changes: this.auditLog
            }));
          } catch (e) { /* silent */ }
        }
      });
    }

    destroy() {
      if (this._saveTimer) clearInterval(this._saveTimer);
    }
  }

  // Auto-initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMetaLayer);
  } else {
    initMetaLayer();
  }

  function initMetaLayer() {
    document.querySelectorAll('[data-meta-config]').forEach(form => {
      const url = form.dataset.metaConfig;
      if (url && !form.dataset.metaInitialized) {
        fetch(url)
          .then(r => r.json())
          .then(config => {
            new MetaLayer(form, config);
            form.dataset.metaInitialized = 'true';
          })
          .catch(err => console.warn('[MetaLayer] Failed to load config:', err));
      }
    });
  }

  // Expose for programmatic use (React, etc.)
  window.MetaLayer = MetaLayer;
})();
