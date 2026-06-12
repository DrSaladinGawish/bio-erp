(function() {
  'use strict';

  class MetaDashboard {
    constructor(container, config) {
      this.el = container;
      this.config = config || {};
      this.kpis = config.kpis || [];
      this.period = localStorage.getItem('meta_dashboard_period') || 'this_month';
      this.refreshTimer = null;
      this.init();
    }

    init() {
      this.startAutoRefresh();
      this.bindDrillDown();
      this.addPeriodToggle();
      this.bindExportActions();
      this.restorePreferences();
    }

    startAutoRefresh() {
      const interval = (this.config.refresh_interval_seconds || 30) * 1000;
      this.refreshTimer = setInterval(() => this.refreshAll(), interval);
    }

    async refreshAll() {
      for (const kpi of this.kpis) {
        const el = this.el.querySelector(`[data-kpi="${kpi.id}"]`);
        if (!el) continue;
        const valueEl = el.querySelector('.kpi-value') || el;
        try {
          const url = kpi.endpoint + '?period=' + this.period;
          const res = await fetch(url);
          const data = await res.json();
          const oldVal = parseFloat(valueEl.dataset.value || '0');
          const newVal = parseFloat(data.value) || 0;
          this.animateValue(valueEl, oldVal, newVal);
          valueEl.dataset.value = newVal;
          el.classList.remove('kpi-error');
          const trendEl = el.querySelector('.kpi-trend');
          if (trendEl && data.trend !== undefined) {
            trendEl.textContent = data.trend >= 0 ? '\u2191 ' + data.trend + '%' : '\u2193 ' + Math.abs(data.trend) + '%';
            trendEl.className = 'kpi-trend ' + (data.trend >= 0 ? 'trend-up' : 'trend-down');
          }
        } catch (e) {
          el.classList.add('kpi-error');
          valueEl.textContent = 'ERR';
        }
      }
    }

    animateValue(el, start, end) {
      const duration = 800;
      const startTime = performance.now();
      const fmt = (v) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      const tick = (now) => {
        const p = Math.min((now - startTime) / duration, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        el.textContent = fmt(start + (end - start) * ease);
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }

    bindDrillDown() {
      this.el.querySelectorAll('[data-kpi]').forEach(kpi => {
        kpi.style.cursor = 'pointer';
        kpi.addEventListener('click', () => {
          const kpiId = kpi.dataset.kpi;
          const kpiDef = this.kpis.find(k => k.id === kpiId);
          if (!kpiDef) return;
          fetch(kpiDef.detail_endpoint + '?period=' + this.period)
            .then(r => r.json())
            .then(data => this.showDrillDownModal(kpiDef.label || kpiId, data))
            .catch(() => {});
        });
      });
    }

    showDrillDownModal(title, data) {
      let modal = document.querySelector('.meta-dashboard-modal');
      if (modal) modal.remove();
      modal = document.createElement('div');
      modal.className = 'meta-dashboard-modal';
      modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:99999;display:flex;align-items:center;justify-content:center;';
      const items = Array.isArray(data) ? data : (data.items || data.data || []);
      const fields = items.length > 0 ? Object.keys(items[0]).slice(0, 6) : [];
      modal.innerHTML = '<div style="background:#fff;border-radius:12px;max-width:800px;width:90%;max-height:80vh;overflow:auto;padding:24px;">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">' +
        '<h3 style="margin:0;">' + title + ' — Details</h3>' +
        '<button onclick="this.closest(\'.meta-dashboard-modal\').remove()" style="background:none;border:none;font-size:1.5rem;cursor:pointer;">\u00d7</button>' +
        '</div>' +
        '<table style="width:100%;border-collapse:collapse;">' +
        '<thead><tr>' + fields.map(f => '<th style="text-align:left;padding:8px;border-bottom:2px solid #e2e8f0;font-weight:600;">' + f + '</th>').join('') + '</tr></thead>' +
        '<tbody>' + items.map(item => '<tr>' + fields.map(f => '<td style="padding:8px;border-bottom:1px solid #e2e8f0;">' + (item[f] ?? '') + '</td>').join('') + '</tr>').join('') + '</tbody>' +
        '</table></div>';
      document.body.appendChild(modal);
      modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
    }

    addPeriodToggle() {
      const periods = [
        { id: 'this_month', label: 'This Month' },
        { id: 'last_month', label: 'Last Month' },
        { id: 'this_quarter', label: 'This Quarter' },
        { id: 'ytd', label: 'YTD' },
        { id: 'custom', label: 'Custom' },
      ];
      const toolbar = document.createElement('div');
      toolbar.className = 'meta-period-toolbar';
      toolbar.style.cssText = 'display:flex;gap:4px;margin-bottom:16px;flex-wrap:wrap;';
      periods.forEach(p => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-sm ' + (p.id === this.period ? 'btn-primary' : 'btn-outline-secondary');
        btn.textContent = p.label;
        btn.dataset.period = p.id;
        btn.addEventListener('click', () => {
          this.period = p.id;
          toolbar.querySelectorAll('button').forEach(b => b.className = 'btn btn-sm btn-outline-secondary');
          btn.className = 'btn btn-sm btn-primary';
          if (p.id === 'custom') {
            const custom = prompt('Enter custom period (e.g. 2024-01 to 2024-03):');
            if (custom) this.period = custom;
          }
          localStorage.setItem('meta_dashboard_period', this.period);
          this.refreshAll();
        });
        toolbar.appendChild(btn);
      });
      this.el.insertBefore(toolbar, this.el.firstChild);
    }

    bindExportActions() {
      this.el.querySelectorAll('[data-chart]').forEach(chart => {
        const actions = document.createElement('div');
        actions.className = 'meta-chart-actions';
        actions.style.cssText = 'display:flex;gap:4px;margin-top:8px;justify-content:flex-end;';
        const chartId = chart.dataset.chart;
        ['PNG', 'CSV', 'Excel'].forEach(fmt => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'btn btn-sm btn-outline-secondary';
          btn.textContent = '\u2b07 ' + fmt;
          btn.addEventListener('click', () => {
            window.open('/api/meta/export/' + chartId + '?format=' + fmt.toLowerCase() + '&period=' + this.period, '_blank');
          });
          actions.appendChild(btn);
        });
        chart.appendChild(actions);
      });
    }

    restorePreferences() {
      const saved = localStorage.getItem('meta_dashboard_period');
      if (saved) {
        this.period = saved;
        const btn = this.el.querySelector('[data-period="' + saved + '"]');
        if (btn) btn.click();
      }
    }

    destroy() {
      if (this.refreshTimer) clearInterval(this.refreshTimer);
    }
  }

  function initDashboards() {
    document.querySelectorAll('[data-meta-dashboard]').forEach(el => {
      if (el.dataset.metaDashboardInit) return;
      const url = el.dataset.metaDashboard;
      if (url) {
        fetch(url).then(r => r.json()).then(config => {
          new MetaDashboard(el, config);
          el.dataset.metaDashboardInit = 'true';
        }).catch(e => console.warn('[MetaDashboard] init error:', e));
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initDashboards);
  else initDashboards();
  window.MetaDashboard = MetaDashboard;
})();
