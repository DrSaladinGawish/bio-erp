/**
 * Event Form Auto-Recognition
 * Auto-suggests services, UOM, and validates capacity.
 */

async function suggestServices(clientId, categoryId) {
    if (!clientId) return;
    let url = `/api/v1/event-ops/recognition/suggest-services?client_id=${clientId}`;
    if (categoryId) url += `&category_id=${categoryId}`;

    try {
        const res = await fetch(url, {
            headers: { 'Authorization': 'Bearer ' + authToken }
        });
        if (!res.ok) return;
        const data = await res.json();
        renderSuggestions(data);
    } catch (e) {
        console.error('Suggest services failed:', e);
    }
}

function renderSuggestions(data) {
    const container = document.getElementById('suggested-services');
    if (!container) return;

    const history = data.client_history || [];
    const template = data.category_template || [];

    let html = '';
    if (history.length > 0) {
        html += '<div class="card-subtitle" style="margin-bottom:8px">Suggested from client history:</div>';
        html += history.slice(0, 5).map(s => `
            <div class="suggestion-item" onclick="applySuggestion(this)" 
                 data-description="${s.description || ''}" 
                 data-uom="${s.uom || ''}" 
                 data-qty="${s.qty || 1}" 
                 data-unit-price="${s.selling_price || s.unit_cost || 0}"
                 style="padding:8px;border:1px solid var(--border-color);border-radius:6px;margin-bottom:4px;cursor:pointer">
                <strong>${s.description || 'Unknown'}</strong>
                <span style="float:right;color:var(--text-muted)">${s.uom || '—'} × ${s.qty || 1} @ ${s.selling_price || 0}</span>
            </div>
        `).join('');
    }

    if (template.length > 0) {
        html += '<div class="card-subtitle" style="margin-bottom:8px;margin-top:12px">Category template:</div>';
        html += template.slice(0, 5).map(t => `
            <div class="suggestion-item" onclick="applyTemplateUom(this)"
                 data-uom="${t.uom_code || ''}" 
                 data-unit-price="${t.default_unit_price || 0}"
                 data-min-qty="${t.min_qty || 1}"
                 data-max-qty="${t.max_qty || ''}"
                 style="padding:8px;border:1px solid var(--border-color);border-radius:6px;margin-bottom:4px;cursor:pointer">
                <strong>${t.uom_name || t.uom_code || '—'}</strong>
                <span style="float:right;color:var(--text-muted)">Default: ${t.default_unit_price || 0} EGP</span>
            </div>
        `).join('');
    }

    if (!html) {
        html = '<div style="color:var(--text-muted);padding:8px">No suggestions available</div>';
    }

    container.innerHTML = html;
}

function applySuggestion(el) {
    const desc = el.dataset.description;
    const uom = el.dataset.uom;
    const qty = el.dataset.qty;
    const price = el.dataset.unitPrice;

    const descInput = document.getElementById('line-item-description');
    const uomInput = document.getElementById('line-item-uom');
    const qtyInput = document.getElementById('line-item-qty');
    const priceInput = document.getElementById('line-item-price');

    if (descInput) descInput.value = desc;
    if (uomInput) uomInput.value = uom;
    if (qtyInput) qtyInput.value = qty;
    if (priceInput) priceInput.value = price;
}

function applyTemplateUom(el) {
    const uom = el.dataset.uom;
    const price = el.dataset.unitPrice;
    const minQty = el.dataset.minQty;
    const maxQty = el.dataset.maxQty;

    const uomInput = document.getElementById('line-item-uom');
    const priceInput = document.getElementById('line-item-price');
    const qtyInput = document.getElementById('line-item-qty');

    if (uomInput) uomInput.value = uom;
    if (priceInput) priceInput.value = price;
    if (qtyInput) qtyInput.value = minQty;
}

async function validateVenueCapacity(pax) {
    if (!pax || pax <= 0) return;

    try {
        const res = await fetch(`/api/v1/event-ops/recognition/validate-capacity?pax=${pax}`, {
            headers: { 'Authorization': 'Bearer ' + authToken }
        });
        if (!res.ok) return;
        const data = await res.json();
        showVenueSuggestions(data);
    } catch (e) {
        console.error('Validate capacity failed:', e);
    }
}

function showVenueSuggestions(data) {
    const container = document.getElementById('venue-suggestions');
    if (!container) return;

    const venues = data.suggested_venues || [];
    if (venues.length === 0) {
        container.innerHTML = '<div style="color:var(--text-muted);padding:8px">No venue suggestions</div>';
        return;
    }

    container.innerHTML = venues.map(v => `
        <div style="padding:8px;border:1px solid var(--border-color);border-radius:6px;margin-bottom:4px">
            <strong>${v.venue || 'Unknown'}</strong>
            <span style="float:right;color:var(--text-muted)">Capacity: ${v.capacity || '—'} pax</span>
        </div>
    `).join('');
}

// Auto-trigger on client selection change
document.addEventListener('DOMContentLoaded', function() {
    const clientSelect = document.getElementById('event-client-select');
    if (clientSelect) {
        clientSelect.addEventListener('change', function() {
            const clientId = parseInt(this.value);
            const categoryId = null;
            const suggestionsContainer = document.getElementById('suggested-services');
            if (suggestionsContainer) {
                suggestionsContainer.innerHTML = '<div style="color:var(--text-muted);padding:8px">Loading suggestions...</div>';
            }
            suggestServices(clientId, categoryId);
        });
    }

    const paxInput = document.getElementById('event-size');
    if (paxInput) {
        paxInput.addEventListener('change', function() {
            validateVenueCapacity(parseInt(this.value));
        });
    }
});
