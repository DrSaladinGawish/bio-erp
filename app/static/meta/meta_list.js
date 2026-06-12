(function() {
  'use strict';

  class MetaList {
    constructor(container, config) {
      this.el = container;
      this.config = config || {};
      this.listKey = config.list_key || this.el.id || 'list';
      this.selected = new Set();
      this.init();
    }

    init() {
      this.addBulkSelect();
      this.addSmartSearch();
      this.addColumnToggle();
      this.addSorting();
      this.restorePreferences();
    }

    addBulkSelect() {
      const table = this.el.querySelector('table');
      if (!table) return;
      const headerRow = table.querySelector('thead tr');
      if (!headerRow) return;
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.className = 'form-check-input meta-select-all';
      cb.addEventListener('change', () => {
        table.querySelectorAll('tbody .meta-select-row').forEach(c => {
          c.checked = cb.checked;
          const row = c.closest('tr');
          if (cb.checked) this.selected.add(row.dataset.id);
          else this.selected.delete(row.dataset.id);
          row.style.background = cb.checked ? 'rgba(6,182,212,0.08)' : '';
        });
        this.updateBulkBar();
      });
      const th = document.createElement('th');
      th.style.width = '40px';
      th.appendChild(cb);
      headerRow.insertBefore(th, headerRow.firstChild);

      table.querySelectorAll('tbody tr').forEach(row => {
        if (!row.dataset.id) return;
        const cb2 = document.createElement('input');
        cb2.type = 'checkbox';
        cb2.className = 'form-check-input meta-select-row';
        cb2.addEventListener('change', () => {
          if (cb2.checked) { this.selected.add(row.dataset.id); row.style.background = 'rgba(6,182,212,0.08)'; }
          else { this.selected.delete(row.dataset.id); row.style.background = ''; }
          this.updateBulkBar();
        });
        const td = document.createElement('td');
        td.appendChild(cb2);
        row.insertBefore(td, row.firstChild);
      });

      const bar = document.createElement('div');
      bar.className = 'meta-bulk-bar alert alert-info d-none';
      bar.style.cssText = 'position:sticky;top:0;z-index:100;display:flex;align-items:center;gap:8px;padding:8px 16px;margin-bottom:8px;';
      bar.innerHTML = '<span class="meta-bulk-count">0 selected</span>';
      (this.config.bulk_actions || ['Delete', 'Export', 'Change Status']).forEach(action => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-sm btn-outline-primary';
        btn.textContent = action;
        btn.addEventListener('click', () => this.executeBulkAction(action));
        bar.appendChild(btn);
      });
      const closeBtn = document.createElement('button');
      closeBtn.type = 'button';
      closeBtn.className = 'btn-close ms-auto';
      closeBtn.addEventListener('click', () => { this.selected.clear(); this.updateBulkBar(); });
      bar.appendChild(closeBtn);
      this.el.insertBefore(bar, this.el.firstChild);
      this._bulkBar = bar;
    }

    updateBulkBar() {
      if (!this._bulkBar) return;
      const count = this.selected.size;
      if (count > 0) {
        this._bulkBar.classList.remove('d-none');
        this._bulkBar.querySelector('.meta-bulk-count').textContent = count + ' selected';
      } else {
        this._bulkBar.classList.add('d-none');
        const table = this.el.querySelector('table');
        if (table) {
          const allCb = table.querySelector('.meta-select-all');
          if (allCb) allCb.checked = false;
        }
      }
    }

    executeBulkAction(action) {
      const ids = Array.from(this.selected);
      const listKey = this.listKey;
      if (action === 'Delete') {
        if (!confirm('Delete ' + ids.length + ' items?')) return;
        fetch('/api/meta/bulk/' + listKey + '/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids })
        }).then(r => r.ok ? location.reload() : alert('Delete failed'));
      } else if (action === 'Export') {
        window.open('/api/meta/bulk/' + listKey + '/export?ids=' + ids.join(','), '_blank');
      } else if (action === 'Change Status') {
        const status = prompt('New status:');
        if (!status) return;
        fetch('/api/meta/bulk/' + listKey + '/status', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids, status })
        }).then(r => r.ok ? location.reload() : alert('Status update failed'));
      }
    }

    addSmartSearch() {
      const existingSearch = this.el.querySelector('input[type="search"], input[name="q"], .meta-search');
      if (existingSearch) return;
      const searchDiv = document.createElement('div');
      searchDiv.className = 'mb-3 meta-search';
      searchDiv.style.cssText = 'position:relative;';
      searchDiv.innerHTML = '<input type="search" class="form-control" placeholder="Search ' + (this.config.title || 'records') + '..." style="padding-right:30px;">';
      const input = searchDiv.querySelector('input');
      const datalist = document.createElement('datalist');
      datalist.id = 'meta-recent-' + this.listKey;
      const recent = JSON.parse(localStorage.getItem('meta_search_recent') || '[]');
      recent.forEach(q => {
        const opt = document.createElement('option');
        opt.value = q;
        datalist.appendChild(opt);
      });
      input.setAttribute('list', datalist.id);
      searchDiv.appendChild(datalist);
      let debounceTimer;
      input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          const q = input.value.trim();
          if (q.length < 2) return;
          let recent = JSON.parse(localStorage.getItem('meta_search_recent') || '[]');
          recent = [q, ...recent.filter(r => r !== q)].slice(0, 10);
          localStorage.setItem('meta_search_recent', JSON.stringify(recent));
          const url = new URL(window.location);
          url.searchParams.set('q', q);
          window.location.href = url.toString();
        }, 400);
      });
      const tableWrapper = this.el.querySelector('table')?.parentElement;
      if (tableWrapper) tableWrapper.parentElement.insertBefore(searchDiv, tableWrapper);
    }

    addColumnToggle() {
      const table = this.el.querySelector('table');
      if (!table) return;
      const headerRow = table.querySelector('thead tr');
      if (!headerRow) return;
      const cols = headerRow.querySelectorAll('th');
      if (cols.length < 3) return;
      const savedHidden = JSON.parse(localStorage.getItem('meta_cols_hidden_' + this.listKey) || '[]');
      const toggleBtn = document.createElement('div');
      toggleBtn.className = 'dropdown d-inline-block ms-2';
      toggleBtn.innerHTML = '<button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">Columns</button><div class="dropdown-menu" style="max-height:300px;overflow-y:auto;"></div>';
      const menu = toggleBtn.querySelector('.dropdown-menu');
      cols.forEach((th, idx) => {
        const label = th.textContent.trim();
        if (idx === 0) return;
        const item = document.createElement('label');
        item.className = 'dropdown-item py-1';
        item.style.cssText = 'display:flex;align-items:center;gap:8px;cursor:pointer;';
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.className = 'form-check-input';
        cb.checked = !savedHidden.includes(String(idx));
        cb.addEventListener('change', () => {
          let hidden = JSON.parse(localStorage.getItem('meta_cols_hidden_' + this.listKey) || '[]');
          if (!cb.checked) { if (!hidden.includes(String(idx))) hidden.push(String(idx)); }
          else { hidden = hidden.filter(h => h !== String(idx)); }
          localStorage.setItem('meta_cols_hidden_' + this.listKey, JSON.stringify(hidden));
          this.applyColumnVisibility();
        });
        item.appendChild(cb);
        item.appendChild(document.createTextNode(label));
        menu.appendChild(item);
      });
      const searchContainer = this.el.querySelector('.meta-search');
      if (searchContainer) searchContainer.appendChild(toggleBtn);
      this._headerCols = cols;
      this.applyColumnVisibility();
    }

    applyColumnVisibility() {
      const hidden = JSON.parse(localStorage.getItem('meta_cols_hidden_' + this.listKey) || '[]');
      const table = this.el.querySelector('table');
      if (!table) return;
      hidden.forEach(idx => {
        table.querySelectorAll('tr').forEach(row => {
          const cell = row.children[parseInt(idx)];
          if (cell) cell.style.display = 'none';
        });
      });
    }

    addSorting() {
      const table = this.el.querySelector('table');
      if (!table) return;
      const headers = table.querySelectorAll('thead th');
      headers.forEach((th, idx) => {
        if (idx === 0) return;
        th.style.cursor = 'pointer';
        th.addEventListener('click', () => {
          const url = new URL(window.location);
          const currentSort = url.searchParams.get('sort');
          const currentDir = url.searchParams.get('dir');
          const field = th.dataset.field || th.textContent.trim().toLowerCase();
          if (currentSort === field && currentDir === 'asc') {
            url.searchParams.set('dir', 'desc');
          } else if (currentSort === field) {
            url.searchParams.delete('sort');
            url.searchParams.delete('dir');
          } else {
            url.searchParams.set('sort', field);
            url.searchParams.set('dir', 'asc');
          }
          window.location.href = url.toString();
        });
      });
    }

    restorePreferences() {
    }
  }

  function initLists() {
    document.querySelectorAll('[data-meta-list]').forEach(el => {
      if (el.dataset.metaListInit) return;
      const url = el.dataset.metaList;
      if (url) {
        fetch(url).then(r => r.json()).then(config => {
          new MetaList(el, config);
          el.dataset.metaListInit = 'true';
        }).catch(e => console.warn('[MetaList] init error:', e));
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initLists);
  else initLists();
  window.MetaList = MetaList;
})();
