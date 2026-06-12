/**
 * Sortable + Paginated Tables (IHE-ERP v2.5.1)
 *
 * Declarative client-side sorting and pagination for HTML tables.
 *
 * Sortable table:
 *   <table data-sortable="true">
 *     <thead><tr>
 *       <th data-sort-type="number">ID</th>
 *       <th data-sort-type="text">Name</th>
 *       <th data-sort-type="date">Date</th>
 *     </tr></thead>
 *     <tbody>...</tbody>
 *   </table>
 *
 * Paginated table:
 *   <table data-paginator="true" data-page-size="10">
 *     ...
 *   </table>
 *   <div class="pagination-controls"></div>
 *
 * Or both:
 *   <table data-sortable="true" data-paginator="true" data-page-size="15">...</table>
 */
(function () {
    'use strict';

    var DEFAULT_PAGE_SIZE = 20;
    var PAGE_SIZE_OPTIONS = [5, 10, 20, 50, 100];

    // ── Sorting ──

    function getCellValue(row, idx) {
        var cell = row.cells[idx];
        if (!cell) return '';
        return cell.textContent.trim();
    }

    function compareValues(a, b, type, dir) {
        var mul = dir === 'asc' ? 1 : -1;
        if (type === 'number') {
            var na = parseFloat(a.replace(/[^0-9.\-]/g, '')) || 0;
            var nb = parseFloat(b.replace(/[^0-9.\-]/g, '')) || 0;
            return (na - nb) * mul;
        }
        if (type === 'date') {
            var da = Date.parse(a) || 0;
            var db = Date.parse(b) || 0;
            return (da - db) * mul;
        }
        return a.localeCompare(b, undefined, { numeric: true }) * mul;
    }

    function initSortable(table) {
        var thead = table.querySelector('thead');
        if (!thead) return;
        var headers = thead.querySelectorAll('th');
        var tbody = table.querySelector('tbody');
        if (!tbody) return;

        for (var i = 0; i < headers.length; i++) {
            (function (colIdx) {
                var th = headers[colIdx];
                th.style.cursor = 'pointer';
                th.style.userSelect = 'none';
                th.title = 'Click to sort';

                // Add sort indicator arrow
                var arrow = document.createElement('span');
                arrow.className = 'sort-arrow';
                arrow.style.cssText = 'margin-left:4px;opacity:0.3;';
                arrow.textContent = '\u2195';
                th.appendChild(arrow);

                th.addEventListener('click', function () {
                    var dir = th.getAttribute('data-sort-dir') === 'asc' ? 'desc' : 'asc';
                    // Reset other headers
                    for (var j = 0; j < headers.length; j++) {
                        headers[j].removeAttribute('data-sort-dir');
                        var a = headers[j].querySelector('.sort-arrow');
                        if (a) a.textContent = '\u2195';
                    }
                    th.setAttribute('data-sort-dir', dir);
                    arrow.textContent = dir === 'asc' ? '\u2191' : '\u2193';
                    arrow.style.opacity = '1';

                    var type = th.getAttribute('data-sort-type') || 'text';
                    var rows = Array.from(tbody.querySelectorAll('tr'));
                    rows.sort(function (a, b) {
                        var va = getCellValue(a, colIdx);
                        var vb = getCellValue(b, colIdx);
                        return compareValues(va, vb, type, dir);
                    });
                    rows.forEach(function (row) { tbody.appendChild(row); });

                    // Re-apply pagination after sorting
                    if (table.hasAttribute('data-paginator')) {
                        applyPagination(table);
                    }
                });
            })(i);
        }
    }

    // ── Pagination ──

    function applyPagination(table) {
        var pageSize = parseInt(table.getAttribute('data-page-size'), 10) || DEFAULT_PAGE_SIZE;
        var tbody = table.querySelector('tbody');
        if (!tbody) return;
        var rows = Array.from(tbody.querySelectorAll('tr'));

        // Build or locate controls container
        var controls = table.nextElementSibling;
        if (!controls || !controls.classList.contains('ihe-pagination')) {
            controls = document.createElement('div');
            controls.className = 'ihe-pagination';
            controls.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:8px 0;font-size:13px;flex-wrap:wrap;gap:8px;';
            table.parentNode.insertBefore(controls, table.nextSibling);
        }

        var totalRows = rows.length;
        var totalPages = Math.max(1, Math.ceil(totalRows / pageSize));

        // Get current page from data attribute
        var currentPage = parseInt(table.getAttribute('data-page'), 10) || 1;
        if (currentPage < 1) currentPage = 1;
        if (currentPage > totalPages) currentPage = totalPages;
        table.setAttribute('data-page', currentPage);

        // Show only current page rows
        var start = (currentPage - 1) * pageSize;
        var end = Math.min(start + pageSize, totalRows);
        for (var i = 0; i < rows.length; i++) {
            rows[i].style.display = (i >= start && i < end) ? '' : 'none';
        }

        // Render controls
        var info = document.createElement('span');
        info.className = 'ihe-page-info';
        info.textContent = 'Showing ' + (start + 1) + '–' + end + ' of ' + totalRows;

        var nav = document.createElement('span');
        nav.className = 'ihe-page-nav';

        function pageBtn(label, page, disabled) {
            var btn = document.createElement('button');
            btn.textContent = label;
            btn.disabled = disabled;
            btn.style.cssText = 'background:' + (disabled ? '#eee' : '#fff') + ';border:1px solid #ccc;border-radius:3px;padding:4px 10px;cursor:' + (disabled ? 'default' : 'pointer') + ';margin:0 2px;font-size:12px;';
            if (!disabled) {
                btn.addEventListener('click', function () {
                    table.setAttribute('data-page', page);
                    applyPagination(table);
                });
            }
            return btn;
        }

        function sizeSelector() {
            var sel = document.createElement('select');
            sel.style.cssText = 'margin-left:8px;padding:3px 6px;font-size:12px;border:1px solid #ccc;border-radius:3px;';
            for (var pi = 0; pi < PAGE_SIZE_OPTIONS.length; pi++) {
                var opt = document.createElement('option');
                opt.value = PAGE_SIZE_OPTIONS[pi];
                opt.textContent = PAGE_SIZE_OPTIONS[pi];
                if (PAGE_SIZE_OPTIONS[pi] === pageSize) opt.selected = true;
                sel.appendChild(opt);
            }
            sel.addEventListener('change', function () {
                table.setAttribute('data-page-size', sel.value);
                table.setAttribute('data-page', 1);
                applyPagination(table);
            });
            return sel;
        }

        nav.appendChild(pageBtn('\u00AB Prev', currentPage - 1, currentPage <= 1));

        // Page number buttons (show at most 7)
        var pageStart = Math.max(1, currentPage - 3);
        var pageEnd = Math.min(totalPages, currentPage + 3);
        if (pageStart > 1) {
            nav.appendChild(pageBtn('1', 1, false));
            if (pageStart > 2) {
                var ell = document.createElement('span');
                ell.textContent = '\u2026';
                ell.style.cssText = 'margin:0 2px;';
                nav.appendChild(ell);
            }
        }
        for (var p = pageStart; p <= pageEnd; p++) {
            var btn = pageBtn(p, p, false);
            if (p === currentPage) {
                btn.style.background = '#1a3a5c';
                btn.style.color = '#fff';
                btn.style.borderColor = '#1a3a5c';
                btn.disabled = true;
            }
            nav.appendChild(btn);
        }
        if (pageEnd < totalPages) {
            if (pageEnd < totalPages - 1) {
                var ell2 = document.createElement('span');
                ell2.textContent = '\u2026';
                ell2.style.cssText = 'margin:0 2px;';
                nav.appendChild(ell2);
            }
            nav.appendChild(pageBtn(totalPages, totalPages, false));
        }

        nav.appendChild(pageBtn('Next \u00BB', currentPage + 1, currentPage >= totalPages));
        nav.appendChild(sizeSelector());

        controls.innerHTML = '';
        controls.appendChild(info);
        controls.appendChild(nav);

        // Show controls
        if (totalPages > 1) {
            controls.style.display = '';
        } else {
            controls.style.display = 'none';
        }
    }

    // ── Init ──

    function init() {
        // Sortable tables
        var sortables = document.querySelectorAll('table[data-sortable="true"]');
        for (var i = 0; i < sortables.length; i++) {
            initSortable(sortables[i]);
        }

        // Paginated tables
        var paginated = document.querySelectorAll('table[data-paginator="true"]');
        for (var j = 0; j < paginated.length; j++) {
            applyPagination(paginated[j]);
        }
    }

    // Re-run on dynamic content (e.g., after AJAX load)
    window.initSortableTables = function (root) {
        root = root || document;
        var tables = root.querySelectorAll('table[data-sortable="true"]');
        for (var i = 0; i < tables.length; i++) {
            initSortable(tables[i]);
        }
        var pTables = root.querySelectorAll('table[data-paginator="true"]');
        for (var j = 0; j < pTables.length; j++) {
            applyPagination(pTables[j]);
        }
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
