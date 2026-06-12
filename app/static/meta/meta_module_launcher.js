(function() {
  'use strict';

  class MetaModuleLauncher {
    constructor(container, config) {
      this.el = container;
      this.config = config || {};
      this.modules = config.modules || [];
      this.history = {};
      this.init();
    }

    init() {
      this.pollStatus();
      setInterval(() => this.pollStatus(), 5000);
      this.bindActions();
    }

    pollStatus() {
      this.modules.forEach(mod => {
        fetch(mod.status_endpoint, { cache: 'no-store' })
          .then(r => r.json())
          .then(data => {
            const card = this.el.querySelector('[data-module="' + mod.id + '"]');
            if (!card) return;
            const dot = card.querySelector('.module-status-dot');
            if (dot) {
              dot.style.background = data.status === 'running' ? '#22c55e' : data.status === 'degraded' ? '#f59e0b' : '#ef4444';
              dot.title = data.status;
            }
            const versionEl = card.querySelector('.module-version');
            if (versionEl) versionEl.textContent = data.version || '';
            if (!this.history[mod.id]) this.history[mod.id] = [];
            this.history[mod.id].push({ time: Date.now(), status: data.status === 'running' ? 1 : 0 });
            if (this.history[mod.id].length > 20) this.history[mod.id].shift();
            this.drawSparkline(card, mod.id);
          })
          .catch(() => {
            const card = this.el.querySelector('[data-module="' + mod.id + '"]');
            if (card) {
              const dot = card.querySelector('.module-status-dot');
              if (dot) { dot.style.background = '#ef4444'; dot.title = 'unreachable'; }
            }
          });
      });
    }

    drawSparkline(card, moduleId) {
      let svg = card.querySelector('.module-sparkline');
      if (!svg) {
        svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'module-sparkline');
        svg.setAttribute('width', '80');
        svg.setAttribute('height', '24');
        svg.setAttribute('viewBox', '0 0 80 24');
        svg.style.cssText = 'display:block;margin-top:4px;';
        card.appendChild(svg);
      }
      const points = this.history[moduleId] || [];
      if (points.length < 2) return;
      const w = 80, h = 24;
      const stepX = w / (points.length - 1);
      const pathD = points.map((p, i) => {
        const x = i * stepX;
        const y = h - (p.status * h);
        return (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1);
      }).join(' ');
      svg.innerHTML = '<path d="' + pathD + '" fill="none" stroke="#22c55e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>';
    }

    bindActions() {
      this.el.querySelectorAll('[data-module-action]').forEach(btn => {
        btn.addEventListener('click', () => {
          const action = btn.dataset.moduleAction;
          const moduleId = btn.closest('[data-module]')?.dataset.module;
          if (!moduleId) return;
          const mod = this.modules.find(m => m.id === moduleId);
          if (!mod) return;
          if (action === 'restart') {
            if (!confirm('Restart ' + (mod.label || moduleId) + '?')) return;
            fetch(mod.restart_endpoint, { method: 'POST' })
              .then(r => r.ok ? btn.textContent = 'Restarting...' : alert('Restart failed'));
          } else if (action === 'deploy') {
            fetch(mod.deploy_endpoint, { method: 'POST' })
              .then(r => r.ok ? btn.textContent = 'Deploying...' : alert('Deploy failed'));
          }
        });
      });
    }
  }

  function initModules() {
    document.querySelectorAll('[data-meta-modules]').forEach(el => {
      if (el.dataset.metaModulesInit) return;
      const url = el.dataset.metaModules;
      if (url) {
        fetch(url).then(r => r.json()).then(config => {
          new MetaModuleLauncher(el, config);
          el.dataset.metaModulesInit = 'true';
        }).catch(e => console.warn('[MetaModules] init error:', e));
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initModules);
  else initModules();
  window.MetaModuleLauncher = MetaModuleLauncher;
})();
