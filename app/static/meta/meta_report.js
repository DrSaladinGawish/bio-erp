(function() {
  'use strict';

  class MetaReport {
    constructor(container, config) {
      this.el = container;
      this.config = config || {};
      this.reportKey = config.report_key || container.id || 'report';
      this.init();
    }

    init() {
      this.addColumnFilters();
      this.addViewTemplates();
      this.addScheduleButton();
      this.addExportButtons();
      this.restoreView();
    }

    addColumnFilters() {
      const table = this.el.querySelector('table');
      if (!table) return;
      const headerRow = table.querySelector('thead tr');
      if (!headerRow) return;
      const filterRow = document.createElement('tr');
      headerRow.querySelectorAll('th').forEach((th, idx) => {
        const td = document.createElement('td');
        if (idx === 0) { filterRow.appendChild(td); return; }
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'form-control form-control-sm';
        input.placeholder = 'Filter...';
        input.style.cssText = 'min-width:60px;font-size:0.75rem;';
        let debounce;
        input.addEventListener('input', () => {
          clearTimeout(debounce);
          debounce = setTimeout(() => this.applyFilters(), 300);
        });
        td.appendChild(input);
        filterRow.appendChild(td);
      });
      headerRow.after(filterRow);
      this._filterRow = filterRow;
    }

    applyFilters() {
      const table = this.el.querySelector('table');
      if (!table) return;
      const filters = [];
      this._filterRow.querySelectorAll('input').forEach((input, idx) => {
        const val = input.value.toLowerCase().trim();
        if (val) filters.push({ col: idx, val });
      });
      table.querySelectorAll('tbody tr').forEach(row => {
        let visible = true;
        filters.forEach(f => {
          const cell = row.children[f.col];
          if (cell && !cell.textContent.toLowerCase().includes(f.val)) visible = false;
        });
        row.style.display = visible ? '' : 'none';
      });
    }

    addViewTemplates() {
      const toolbar = document.createElement('div');
      toolbar.className = 'd-flex gap-2 align-items-center mb-2';
      const saveBtn = document.createElement('button');
      saveBtn.type = 'button';
      saveBtn.className = 'btn btn-sm btn-outline-primary';
      saveBtn.textContent = '\ud83d\udcbe Save View';
      saveBtn.addEventListener('click', () => {
        const name = prompt('View name:');
        if (!name) return;
        const views = JSON.parse(localStorage.getItem('meta_report_views_' + this.reportKey) || '[]');
        const filters = [];
        if (this._filterRow) {
          this._filterRow.querySelectorAll('input').forEach(input => filters.push(input.value));
        }
        views.push({ name, filters, savedAt: new Date().toISOString() });
        localStorage.setItem('meta_report_views_' + this.reportKey, JSON.stringify(views));
        this.renderSavedViews();
      });
      toolbar.appendChild(saveBtn);
      const viewSelect = document.createElement('select');
      viewSelect.className = 'form-select form-select-sm';
      viewSelect.style.width = 'auto';
      viewSelect.innerHTML = '<option value="">Saved Views...</option>';
      viewSelect.addEventListener('change', () => {
        if (!viewSelect.value) return;
        const views = JSON.parse(localStorage.getItem('meta_report_views_' + this.reportKey) || '[]');
        const view = views.find(v => v.name === viewSelect.value);
        if (view && view.filters) {
          if (this._filterRow) {
            this._filterRow.querySelectorAll('input').forEach((input, i) => { input.value = view.filters[i] || ''; });
          }
          this.applyFilters();
        }
      });
      toolbar.appendChild(viewSelect);
      this._viewSelect = viewSelect;
      this.el.insertBefore(toolbar, this.el.firstChild);
      this.renderSavedViews();
    }

    renderSavedViews() {
      if (!this._viewSelect) return;
      const views = JSON.parse(localStorage.getItem('meta_report_views_' + this.reportKey) || '[]');
      this._viewSelect.innerHTML = '<option value="">Saved Views...</option>';
      views.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.name;
        opt.textContent = v.name;
        this._viewSelect.appendChild(opt);
      });
    }

    addScheduleButton() {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-sm btn-outline-secondary';
      btn.textContent = '\u23f0 Schedule';
      btn.addEventListener('click', () => {
        const email = prompt('Email to send report to:');
        const schedule = prompt('Schedule (daily/weekly/monthly):');
        if (!email || !schedule) return;
        fetch('/api/meta/report/' + this.reportKey + '/schedule', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, schedule, filters: this.getCurrentFilters() })
        }).then(r => r.ok ? alert('Scheduled!') : alert('Failed'));
      });
      const tb = this.el.querySelector('.d-flex.gap-2');
      if (tb) tb.appendChild(btn);
    }

    addExportButtons() {
      const tb = this.el.querySelector('.d-flex.gap-2') || this.el.querySelector('h2, h3')?.nextElementSibling;
      if (!tb) return;
      ['PDF', 'CSV', 'Excel'].forEach(fmt => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-sm btn-outline-secondary';
        btn.textContent = '\u2b07 ' + fmt;
        btn.addEventListener('click', () => {
          window.open('/api/meta/report/' + this.reportKey + '/export?format=' + fmt.toLowerCase(), '_blank');
        });
        tb.appendChild(btn);
      });
    }

    getCurrentFilters() {
      const filters = {};
      if (this._filterRow) {
        this._filterRow.querySelectorAll('input').forEach((input, idx) => {
          if (input.value) filters['col_' + idx] = input.value;
        });
      }
      return filters;
    }

    restoreView() {
    }
  }

  function initReports() {
    document.querySelectorAll('[data-meta-report]').forEach(el => {
      if (el.dataset.metaReportInit) return;
      const url = el.dataset.metaReport;
      if (url) {
        fetch(url).then(r => r.json()).then(config => {
          new MetaReport(el, config);
          el.dataset.metaReportInit = 'true';
        }).catch(e => console.warn('[MetaReport] init error:', e));
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initReports);
  else initReports();
  window.MetaReport = MetaReport;
})();
