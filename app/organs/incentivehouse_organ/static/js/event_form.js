/**
 * Event Form — Auto-Recovery & Service Suggestions (IHE-ERP v2.5.0)
 * Provides:
 *   suggestServices(clientId, categoryId) — fetches client history + defaults
 *   validateVenueCapacity(venue, pax)     — checks historical pax limits
 *   applySuggestion(service, price, qty)  — fills a line item row
 *   applyTemplateUom(uomCode)            — fills default UOM values
 */

async function suggestServices(clientId, categoryId) {
    if (!clientId) return;
    try {
        const r = await fetch(
            '/api/v1/event-ops/recognition/suggest-services?client_id=' +
            encodeURIComponent(clientId) +
            '&category_id=' + (categoryId || 0)
        );
        const data = await r.json();
        const container = document.getElementById('service-suggestions');
        if (!container) return;
        if (data.client_history && data.client_history.length > 0) {
            let html = '<div class="alert alert-info"><strong>Suggested from client history:</strong><ul>';
            data.client_history.forEach(function(svc) {
                html += '<li>' + svc.service + ' (' + svc.qty + ' x ' + svc.price + ')' +
                    ' <button type="button" class="btn btn-ghost" style="padding:2px 8px;font-size:11px;" ' +
                    'onclick="applySuggestion(\'' + svc.service.replace(/'/g, "\\'") + '\',' + svc.price + ',' + svc.qty + ')">Apply</button></li>';
            });
            html += '</ul></div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '';
        }
        const defaultsContainer = document.getElementById('uom-defaults');
        if (defaultsContainer && data.category_defaults && data.category_defaults.length > 0) {
            let html = '<div class="alert alert-info"><strong>Category UOM templates:</strong><ul>';
            data.category_defaults.forEach(function(d) {
                html += '<li>' + (d.name || d.uom) + ' (' + d.uom + ')' +
                    (d.default_price ? ' — ' + d.default_price : '') +
                    ' <button type="button" class="btn btn-ghost" style="padding:2px 8px;font-size:11px;" ' +
                    'onclick="applyTemplateUom(\'' + d.uom + '\',' + (d.default_price || 0) + ')">Apply</button></li>';
            });
            html += '</ul></div>';
            defaultsContainer.innerHTML = html;
        }
    } catch (err) {
        console.warn('SuggestServices error:', err);
    }
}

async function validateVenueCapacity(venue, pax) {
    if (!venue || !pax) return;
    try {
        const r = await fetch(
            '/api/v1/event-ops/recognition/validate-capacity?venue=' +
            encodeURIComponent(venue) +
            '&pax=' + encodeURIComponent(pax)
        );
        const data = await r.json();
        const el = document.getElementById('capacity-warning');
        if (!el) return;
        if (data.status === 'WARNING') {
            el.innerHTML = '<div class="alert alert-warning">' +
                '⚠️ ' + venue + ' historically max ' + data.max_observed + ' pax. ' +
                (data.suggestion || '') + '</div>';
        } else {
            el.innerHTML = '<div class="alert alert-success">' +
                '✅ ' + venue + ' can handle ' + pax + ' pax (max observed: ' + data.max_observed + ')</div>';
        }
    } catch (err) {
        console.warn('ValidateCapacity error:', err);
    }
}

function applySuggestion(service, price, qty) {
    const table = document.getElementById('line-items-table');
    if (!table) return;
    const lastRow = table.querySelector('tr:last-child');
    if (lastRow) {
        const descInput = lastRow.querySelector('input[name$="description"]');
        const priceInput = lastRow.querySelector('input[name$="unit_price"]');
        const qtyInput = lastRow.querySelector('input[name$="quantity"]');
        if (descInput) descInput.value = service;
        if (priceInput) priceInput.value = price;
        if (qtyInput) qtyInput.value = qty;
    }
}

function applyTemplateUom(uomCode, defaultPrice) {
    const uomSelect = document.querySelector('select[name$="uom"]');
    if (uomSelect) {
        for (var i = 0; i < uomSelect.options.length; i++) {
            if (uomSelect.options[i].value === uomCode) {
                uomSelect.selectedIndex = i;
                break;
            }
        }
    }
    if (defaultPrice && defaultPrice > 0) {
        const priceInput = document.querySelector('input[name$="unit_price"]');
        if (priceInput) priceInput.value = defaultPrice;
    }
}

// Auto-trigger on client select change
document.addEventListener('change', function(e) {
    if (e.target && e.target.matches && e.target.matches('select[name$="client_id"], #client-select')) {
        const val = e.target.value;
        if (val) {
            const catEl = document.querySelector('select[name$="category_id"], #category-select');
            const catId = catEl ? catEl.value : 0;
            suggestServices(val, catId);
        }
    }
    if (e.target && e.target.matches && e.target.matches('input[name$="venue"], #venue-input')) {
        const paxEl = document.querySelector('input[name$="actual_pax"], #pax-input');
        const pax = paxEl ? paxEl.value : 0;
        if (e.target.value && pax > 0) validateVenueCapacity(e.target.value, pax);
    }
    if (e.target && e.target.matches && e.target.matches('input[name$="actual_pax"], #pax-input')) {
        const venueEl = document.querySelector('input[name$="venue"], #venue-input');
        const venue = venueEl ? venueEl.value : '';
        if (venue && e.target.value > 0) validateVenueCapacity(venue, e.target.value);
    }
});
