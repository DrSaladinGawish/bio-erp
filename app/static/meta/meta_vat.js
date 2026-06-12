// Meta Layer VAT Plugin
// Auto-detected and initialized on forms with VAT fields

(function() {
  'use strict';

  class MetaVAT {
    constructor(formEl, config) {
      this.form = formEl;
      this.config = config || {};
      this.vatRateField = this.config.vatRateField || this.findField('vatRate', 'VATRate', 'vat_rate');
      this.subtotalField = this.config.subtotalField || this.findField('subtotal', 'SubTotal');
      this.vatAmountField = this.config.vatAmountField || this.findField('vatAmount', 'VATAmount', 'vat_amount');
      this.totalField = this.config.totalField || this.findField('total', 'TotalValue', 'total', 'total_amount');
      this.taxIdFields = this.config.taxIdFields || [];
      this.init();
    }

    findField(...names) {
      for (const name of names) {
        const el = this.form.querySelector(`[name="${name}"]`);
        if (el) return el;
      }
      return null;
    }

    init() {
      this.bindVATCalc();
      this.bindTaxIDValidation();
      this.bindRatePresets();
    }

    bindVATCalc() {
      const triggerFields = [this.subtotalField, this.vatRateField].filter(Boolean);
      const recalc = () => {
        const subtotal = parseFloat(this.subtotalField?.value) || 0;
        const rate = parseFloat(this.vatRateField?.value) || 0;
        const vat = subtotal * rate / 100;
        const total = subtotal + vat;
        if (this.vatAmountField) {
          this.vatAmountField.value = vat.toFixed(2);
          this.vatAmountField.dispatchEvent(new Event('change', { bubbles: true }));
        }
        if (this.totalField) {
          this.totalField.value = total.toFixed(2);
          this.totalField.dispatchEvent(new Event('change', { bubbles: true }));
        }
      };
      triggerFields.forEach(el => {
        el.addEventListener('input', recalc);
        el.addEventListener('change', recalc);
      });
      // Initial calc
      recalc();
    }

    bindTaxIDValidation() {
      this.form.querySelectorAll('[data-tax-id]').forEach(el => {
        el.addEventListener('blur', () => {
          const val = el.value.replace(/\s/g, '');
          if (!val) return;
          // Egyptian Tax ID format: 9 digits
          const isValid = /^\d{9}$/.test(val);
          if (!isValid) {
            el.style.borderColor = 'var(--accent-red, #ef4444)';
            this.showFieldError(el, 'Tax ID must be exactly 9 digits');
          } else {
            el.style.borderColor = '';
            this.clearFieldError(el);
          }
        });
      });
    }

    bindRatePresets() {
      if (!this.vatRateField) return;
      // Add preset buttons if container exists
      const container = this.vatRateField.closest('.mb-3') || this.vatRateField.parentElement;
      const presets = this.config.vatRates || [0, 5, 14];
      const btnGroup = document.createElement('div');
      btnGroup.className = 'd-flex gap-1 mt-1';
      btnGroup.style.cssText = 'flex-wrap:wrap;';
      presets.forEach(rate => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-sm btn-outline-secondary';
        btn.textContent = rate + '%';
        btn.addEventListener('click', () => {
          this.vatRateField.value = rate;
          this.vatRateField.dispatchEvent(new Event('input', { bubbles: true }));
          this.vatRateField.dispatchEvent(new Event('change', { bubbles: true }));
        });
        btnGroup.appendChild(btn);
      });
      container.appendChild(btnGroup);
    }

    showFieldError(el, msg) {
      let err = el.parentElement.querySelector('.meta-error');
      if (!err) {
        err = document.createElement('div');
        err.className = 'meta-error';
        err.style.cssText = 'color:var(--accent-red,#ef4444);font-size:0.75rem;margin-top:2px;';
        el.parentElement.appendChild(err);
      }
      err.textContent = msg;
    }

    clearFieldError(el) {
      const err = el.parentElement.querySelector('.meta-error');
      if (err) err.textContent = '';
    }
  }

  // Auto-initialize on forms with VAT fields
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-meta-vat]').forEach(form => {
      if (!form.dataset.metaVatInitialized) {
        let config = {};
        try { config = JSON.parse(form.dataset.metaVat); } catch(e) {}
        new MetaVAT(form, config);
        form.dataset.metaVatInitialized = 'true';
      }
    });
  });

  window.MetaVAT = MetaVAT;
})();
