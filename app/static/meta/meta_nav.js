(function() {
  'use strict';

  class MetaNav {
    constructor(container, config) {
      this.el = container;
      this.config = config || {};
      this.navKey = config.nav_key || 'main';
      this.init();
    }

    init() {
      this.highlightCurrent();
      this.loadBadges();
      this.addCollapsibleSections();
      this.addHealthIndicators();
    }

    highlightCurrent() {
      const path = window.location.pathname;
      this.el.querySelectorAll('a').forEach(a => {
        const href = a.getAttribute('href');
        if (href && path.startsWith(href) && href !== '/') {
          a.classList.add('active');
          a.closest('.nav-section')?.classList.add('expanded');
          let parent = a.closest('.collapse');
          if (parent) {
            parent.classList.add('show');
            const trigger = document.querySelector('[data-bs-target="#' + parent.id + '"]');
            if (trigger) trigger.classList.remove('collapsed');
          }
        }
      });
    }

    loadBadges() {
      (this.config.badges || []).forEach(badge => {
        const el = this.el.querySelector('[data-nav-badge="' + badge.id + '"]');
        if (!el) return;
        fetch(badge.endpoint)
          .then(r => r.json())
          .then(data => {
            const count = data.count || data.value || 0;
            if (count > 0) {
              el.style.display = 'inline-flex';
              el.textContent = count > 99 ? '99+' : count;
              el.className = 'badge ' + (count > badge.warn_threshold ? 'bg-danger' : 'bg-secondary');
            }
          })
          .catch(() => {});
      });
    }

    addCollapsibleSections() {
      this.el.querySelectorAll('.nav-section').forEach(section => {
        const header = section.querySelector('.nav-section-header');
        const body = section.querySelector('.nav-section-body');
        if (!header || !body) return;
        const sectionId = section.id || this.navKey + '_' + Array.from(section.parentElement.children).indexOf(section);
        const saved = localStorage.getItem('meta_nav_collapsed_' + sectionId);
        if (saved === 'true') {
          body.style.display = 'none';
        }
        header.style.cursor = 'pointer';
        header.addEventListener('click', () => {
          const collapsed = body.style.display === 'none';
          body.style.display = collapsed ? '' : 'none';
          localStorage.setItem('meta_nav_collapsed_' + sectionId, String(!collapsed));
        });
      });
    }

    addHealthIndicators() {
      this.el.querySelectorAll('[data-health-endpoint]').forEach(el => {
        const url = el.dataset.healthEndpoint;
        const dot = document.createElement('span');
        dot.className = 'health-dot';
        dot.style.cssText = 'display:inline-block;width:8px;height:8px;border-radius:50%;margin-left:8px;';
        el.appendChild(dot);
        const check = () => {
          fetch(url, { method: 'HEAD', cache: 'no-store' })
            .then(r => { dot.style.background = r.ok ? '#22c55e' : '#ef4444'; })
            .catch(() => { dot.style.background = '#ef4444'; });
        };
        check();
        setInterval(check, 30000);
      });
    }
  }

  function initNavs() {
    document.querySelectorAll('[data-meta-nav]').forEach(el => {
      if (el.dataset.metaNavInit) return;
      const url = el.dataset.metaNav;
      if (url) {
        fetch(url).then(r => r.json()).then(config => {
          new MetaNav(el, config);
          el.dataset.metaNavInit = 'true';
        }).catch(e => console.warn('[MetaNav] init error:', e));
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initNavs);
  else initNavs();
  window.MetaNav = MetaNav;
})();
