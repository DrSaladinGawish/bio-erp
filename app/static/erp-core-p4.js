/**
 * P4 FRONTEND API WIRING
 * Connects HTML forms to real BIO-ERP API endpoints
 * Replaces demo data fallback with live PostgreSQL calls
 */

// =========================================================
// UPDATED CONFIGURATION - Production API URLs
// =========================================================
const ERP_CONFIG = {
    // Base API URL - auto-detect based on current host
    API_BASE_URL: (() => {
        const host = window.location.hostname;
        const port = window.location.port || '8000';
        // If served from FastAPI static files, use same origin
        if (host === 'localhost' || host === '127.0.0.1') {
            return `http://${host}:${port}/api/v1`;
        }
        return `/api/v1`;  // Production relative path
    })(),

    // Module endpoints
    ENDPOINTS: {
        transactions: '/transactions',
        or_module: '/or',
        scm_module: '/scm',
        ai_ingest: '/ai-ingest',
        health: '/health'
    },

    COMPANY_NAME: 'Incentive House',
    COMPANY_TAGLINE: 'Enterprise Resource Planning',
    VERSION: '2.1.0-P4',
    DATE_FORMAT: 'YYYY-MM-DD',
    CURRENCY: 'USD',
    CURRENCY_SYMBOL: '$',
    DECIMAL_PLACES: 2,

    // Feature flags
    FEATURES: {
        real_api: true,        // Set to false to use demo data only
        or_module: true,
        scm_module: true,
        auto_refresh: true,    // Auto-refresh transaction list
        refresh_interval: 30000  // 30 seconds
    }
};

// =========================================================
// ENHANCED API CLIENT with error handling & auth
// =========================================================
class ERPApiClient {
    constructor(baseURL = ERP_CONFIG.API_BASE_URL) {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
        this.requestCount = 0;
        this.errorCount = 0;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            ...options,
            headers: {
                ...this.defaultHeaders,
                ...options.headers
            }
        };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        this.requestCount++;
        console.log(`[API] ${config.method || 'GET'} ${url}`);

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                this.errorCount++;
                throw new ApiError(
                    errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`,
                    response.status,
                    errorData
                );
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            return await response.text();
        } catch (error) {
            if (error instanceof ApiError) throw error;

            // Network error - check if API is down
            if (error.message.includes('fetch') || error.message.includes('NetworkError')) {
                this.errorCount++;
                throw new ApiError(
                    'Cannot connect to BIO-ERP server. Please verify the backend is running on port 8000.',
                    0,
                    { originalError: error.message }
                );
            }

            throw new ApiError(error.message, 0, {});
        }
    }

    get(endpoint) { return this.request(endpoint, { method: 'GET' }); }
    post(endpoint, data) { return this.request(endpoint, { method: 'POST', body: data }); }
    put(endpoint, data) { return this.request(endpoint, { method: 'PUT', body: data }); }
    patch(endpoint, data) { return this.request(endpoint, { method: 'PATCH', body: data }); }
    delete(endpoint) { return this.request(endpoint, { method: 'DELETE' }); }

    getStats() {
        return { requests: this.requestCount, errors: this.errorCount };
    }
}

class ApiError extends Error {
    constructor(message, status, data) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
    }
}

const api = new ERPApiClient();

// =========================================================
// HEALTH CHECK & MODULE STATUS
// =========================================================
class SystemMonitor {
    constructor() {
        this.modules = {
            bio_erp: { status: 'unknown', url: '/health', last_check: null },
            or_module: { status: 'unknown', url: '/or/health', last_check: null },
            scm_module: { status: 'unknown', url: '/scm/health', last_check: null }
        };
    }

    async checkAll() {
        const results = {};

        for (const [name, config] of Object.entries(this.modules)) {
            try {
                const data = await api.get(config.url);
                this.modules[name].status = 'online';
                this.modules[name].last_check = new Date();
                results[name] = { status: 'online', data };
            } catch (e) {
                this.modules[name].status = 'offline';
                this.modules[name].last_check = new Date();
                results[name] = { status: 'offline', error: e.message };
            }
        }

        this.updateUI(results);
        return results;
    }

    updateUI(results) {
        // Update footer status dots
        document.querySelectorAll('.module-status').forEach(el => {
            const module = el.dataset.module;
            if (module && results[module]) {
                const isOnline = results[module].status === 'online';
                el.className = `module-status ${isOnline ? 'online' : 'offline'}`;
                el.title = `${module}: ${results[module].status}`;
            }
        });
    }
}

const systemMonitor = new SystemMonitor();

// =========================================================
// TOAST, MODAL, FORM UTILITIES (unchanged from core)
// =========================================================
class ToastManager {
    constructor() {
        this.container = null;
        this.init();
    }
    init() {
        if (!document.getElementById('toast-container')) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('toast-container');
        }
    }
    show(message, title = '', type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
        toast.innerHTML = `
            <span class="toast-icon">${icons[type]}</span>
            <div class="toast-content">
                ${title ? `<div class="toast-title">${title}</div>` : ''}
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        this.container.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('hiding');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
    success(message, title = 'Success') { this.show(message, title, 'success'); }
    error(message, title = 'Error') { this.show(message, title, 'error', 8000); }
    warning(message, title = 'Warning') { this.show(message, title, 'warning', 7000); }
    info(message, title = 'Info') { this.show(message, title, 'info'); }
}

const toast = new ToastManager();

class ModalManager {
    constructor() { this.activeModal = null; }
    open(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        modal.classList.add('active');
        this.activeModal = modal;
        document.body.style.overflow = 'hidden';
        modal.addEventListener('click', (e) => { if (e.target === modal) this.close(modalId); });
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape') this.close(modalId); });
    }
    close(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        modal.classList.remove('active');
        this.activeModal = null;
        document.body.style.overflow = '';
    }
}

const modal = new ModalManager();

const FormatUtils = {
    date(date, format = 'YYYY-MM-DD') {
        if (!date) return '';
        const d = new Date(date);
        if (isNaN(d.getTime())) return date;
        const pad = (n) => String(n).padStart(2, '0');
        return format
            .replace('YYYY', d.getFullYear())
            .replace('MM', pad(d.getMonth() + 1))
            .replace('DD', pad(d.getDate()));
    },
    currency(amount, symbol = ERP_CONFIG.CURRENCY_SYMBOL) {
        if (amount === null || amount === undefined) return '';
        const num = parseFloat(amount);
        if (isNaN(num)) return amount;
        return symbol + num.toLocaleString('en-US', {
            minimumFractionDigits: ERP_CONFIG.DECIMAL_PLACES,
            maximumFractionDigits: ERP_CONFIG.DECIMAL_PLACES
        });
    },
    statusBadge(status) {
        const classes = {
            'draft': 'status-draft',
            'posted': 'status-posted',
            'void': 'status-void',
            'pending': 'status-pending',
            'active': 'status-posted',
            'inactive': 'status-void',
            'staged': 'status-pending'
        };
        const className = classes[status.toLowerCase()] || 'status-pending';
        return `<span class="status-badge ${className}">${status}</span>`;
    }
};

const FormUtils = {
    serialize(form) {
        const formData = new FormData(form);
        const data = {};
        formData.forEach((value, key) => {
            if (data[key]) {
                if (!Array.isArray(data[key])) data[key] = [data[key]];
                data[key].push(value);
            } else {
                data[key] = value;
            }
        });
        return data;
    },
    validate(form) {
        const errors = [];
        form.querySelectorAll('[required]').forEach(field => {
            if (!field.value.trim()) {
                errors.push({ field: field.name, message: `${field.getAttribute('data-label') || field.name} is required` });
                field.classList.add('is-invalid');
            } else {
                field.classList.remove('is-invalid');
            }
        });
        return { valid: errors.length === 0, errors };
    },
    clearErrors(form) {
        form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    },
    reset(form) { form.reset(); this.clearErrors(form); },
    populate(form, data) {
        Object.keys(data).forEach(key => {
            const field = form.querySelector(`[name="${key}"]`);
            if (field) field.value = data[key] || '';
        });
    }
};

class LoadingState {
    static show(element, message = 'Loading...') {
        element.style.position = 'relative';
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div style="text-align: center;">
                <div class="spinner" style="width: 40px; height: 40px; margin: 0 auto 12px;"></div>
                <div style="color: var(--gray-600); font-size: 0.9rem;">${message}</div>
            </div>`;
        element.appendChild(overlay);
        return overlay;
    }
    static hide(element) {
        const overlay = element.querySelector('.loading-overlay');
        if (overlay) overlay.remove();
    }
}

function confirmDialog(message, title = 'Confirm') {
    return new Promise((resolve) => {
        const modalId = 'confirm-modal';
        const existing = document.getElementById(modalId);
        if (existing) existing.remove();

        const modalEl = document.createElement('div');
        modalEl.id = modalId;
        modalEl.className = 'modal-overlay';
        modalEl.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h3 class="modal-title">${title}</h3>
                    <button class="modal-close" onclick="modal.close('${modalId}')">×</button>
                </div>
                <div class="modal-body"><p>${message}</p></div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="modal.close('${modalId}')">Cancel</button>
                    <button class="btn btn-danger" id="confirm-btn">Confirm</button>
                </div>
            </div>`;
        document.body.appendChild(modalEl);
        modal.open(modalId);

        document.getElementById('confirm-btn').addEventListener('click', () => {
            modal.close(modalId);
            resolve(true);
        });
        modalEl.addEventListener('click', (e) => {
            if (e.target === modalEl) { modal.close(modalId); resolve(false); }
        });
    });
}

// =========================================================
// INITIALIZATION
// =========================================================
document.addEventListener('DOMContentLoaded', () => {
    // Set company info
    document.querySelectorAll('.company-name').forEach(el => el.textContent = ERP_CONFIG.COMPANY_NAME);
    document.querySelectorAll('.company-tagline').forEach(el => el.textContent = ERP_CONFIG.COMPANY_TAGLINE);
    document.querySelectorAll('.version-number').forEach(el => el.textContent = `v${ERP_CONFIG.VERSION}`);
    document.querySelectorAll('.current-date').forEach(el => {
        el.textContent = FormatUtils.date(new Date(), 'YYYY-MM-DD');
    });

    // Check system health
    if (ERP_CONFIG.FEATURES.real_api) {
        systemMonitor.checkAll();
    }
});

window.ERP_CONFIG = ERP_CONFIG;
window.api = api;
window.toast = toast;
window.modal = modal;
window.FormatUtils = FormatUtils;
window.FormUtils = FormUtils;
window.LoadingState = LoadingState;
window.confirmDialog = confirmDialog;
window.systemMonitor = systemMonitor;
