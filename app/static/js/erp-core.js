/**
 * INCENTIVE HOUSE ERP - Core JavaScript Module
 * API Client, UI Utilities, and Common Functions
 */

// =========================================================
// CONFIGURATION
// =========================================================
const ERP_CONFIG = {
    API_BASE_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:8000'
        : '',
    COMPANY_NAME: 'Incentive House',
    COMPANY_TAGLINE: 'Enterprise Resource Planning',
    VERSION: '2.0.0',
    DATE_FORMAT: 'YYYY-MM-DD',
    CURRENCY: 'AED',
    CURRENCY_SYMBOL: 'AED ',
    DECIMAL_PLACES: 2
};

// =========================================================
// API CLIENT
// =========================================================
class ERPApiClient {
    constructor(baseURL = ERP_CONFIG.API_BASE_URL) {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
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

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new ApiError(
                    errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
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
            throw new ApiError(error.message, 0, {});
        }
    }

    // HTTP Methods
    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    post(endpoint, data) {
        return this.request(endpoint, { method: 'POST', body: data });
    }

    put(endpoint, data) {
        return this.request(endpoint, { method: 'PUT', body: data });
    }

    patch(endpoint, data) {
        return this.request(endpoint, { method: 'PATCH', body: data });
    }

    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
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

// Global API instance
const api = new ERPApiClient();

// =========================================================
// TOAST NOTIFICATIONS
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

        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };

        toast.innerHTML = `
            <span class="toast-icon">${icons[type]}</span>
            <div class="toast-content">
                ${title ? `<div class="toast-title">${title}</div>` : ''}
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;

        this.container.appendChild(toast);

        // Auto remove
        setTimeout(() => {
            toast.classList.add('hiding');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    success(message, title = 'Success') {
        this.show(message, title, 'success');
    }

    error(message, title = 'Error') {
        this.show(message, title, 'error', 8000);
    }

    warning(message, title = 'Warning') {
        this.show(message, title, 'warning', 7000);
    }

    info(message, title = 'Info') {
        this.show(message, title, 'info');
    }
}

const toast = new ToastManager();

// =========================================================
// MODAL MANAGER
// =========================================================
class ModalManager {
    constructor() {
        this.activeModal = null;
    }

    open(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;

        modal.classList.add('active');
        this.activeModal = modal;
        document.body.style.overflow = 'hidden';

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.close(modalId);
        });

        // Close on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.close(modalId);
        });
    }

    close(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;

        modal.classList.remove('active');
        this.activeModal = null;
        document.body.style.overflow = '';
    }

    closeAll() {
        document.querySelectorAll('.modal-overlay.active').forEach(m => {
            m.classList.remove('active');
        });
        this.activeModal = null;
        document.body.style.overflow = '';
    }
}

const modal = new ModalManager();

// =========================================================
// FORM UTILITIES
// =========================================================
class FormUtils {
    static serialize(form) {
        const formData = new FormData(form);
        const data = {};

        formData.forEach((value, key) => {
            if (data[key]) {
                if (!Array.isArray(data[key])) {
                    data[key] = [data[key]];
                }
                data[key].push(value);
            } else {
                data[key] = value;
            }
        });

        return data;
    }

    static validate(form) {
        const errors = [];
        const required = form.querySelectorAll('[required]');

        required.forEach(field => {
            if (!field.value.trim()) {
                errors.push({
                    field: field.name,
                    message: `${field.getAttribute('data-label') || field.name} is required`
                });
                field.classList.add('is-invalid');
            } else {
                field.classList.remove('is-invalid');
            }
        });

        return {
            valid: errors.length === 0,
            errors
        };
    }

    static clearErrors(form) {
        form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
        form.querySelectorAll('.form-error').forEach(el => el.classList.remove('show'));
    }

    static showErrors(form, errors) {
        errors.forEach(error => {
            const field = form.querySelector(`[name="${error.field}"]`);
            if (field) {
                field.classList.add('is-invalid');
                const errorEl = form.querySelector(`[data-error="${error.field}"]`);
                if (errorEl) {
                    errorEl.textContent = error.message;
                    errorEl.classList.add('show');
                }
            }
        });
    }

    static reset(form) {
        form.reset();
        this.clearErrors(form);
    }

    static populate(form, data) {
        Object.keys(data).forEach(key => {
            const field = form.querySelector(`[name="${key}"]`);
            if (field) {
                field.value = data[key] || '';
            }
        });
    }
}

// =========================================================
// DATA TABLE UTILITIES
// =========================================================
class DataTable {
    constructor(tableId, options = {}) {
        this.table = document.getElementById(tableId);
        this.options = {
            sortable: true,
            searchable: true,
            paginate: true,
            pageSize: 25,
            ...options
        };
        this.data = [];
        this.filteredData = [];
        this.currentPage = 1;
        this.sortColumn = null;
        this.sortDirection = 'asc';

        if (this.table) {
            this.init();
        }
    }

    init() {
        // Add search if enabled
        if (this.options.searchable) {
            this.setupSearch();
        }

        // Add pagination if enabled
        if (this.options.paginate) {
            this.setupPagination();
        }
    }

    setupSearch() {
        const searchInput = document.querySelector(`[data-table-search="${this.table.id}"]`);
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.search(e.target.value);
            });
        }
    }

    setupPagination() {
        const pagination = document.querySelector(`[data-table-pagination="${this.table.id}"]`);
        if (pagination) {
            this.paginationContainer = pagination;
        }
    }

    setData(data) {
        this.data = data;
        this.filteredData = [...data];
        this.currentPage = 1;
        this.render();
    }

    search(query) {
        if (!query) {
            this.filteredData = [...this.data];
        } else {
            const lowerQuery = query.toLowerCase();
            this.filteredData = this.data.filter(row => {
                return Object.values(row).some(val => 
                    String(val).toLowerCase().includes(lowerQuery)
                );
            });
        }
        this.currentPage = 1;
        this.render();
    }

    sort(column) {
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }

        this.filteredData.sort((a, b) => {
            let aVal = a[column];
            let bVal = b[column];

            if (typeof aVal === 'string') aVal = aVal.toLowerCase();
            if (typeof bVal === 'string') bVal = bVal.toLowerCase();

            if (aVal < bVal) return this.sortDirection === 'asc' ? -1 : 1;
            if (aVal > bVal) return this.sortDirection === 'asc' ? 1 : -1;
            return 0;
        });

        this.render();
    }

    render() {
        const tbody = this.table.querySelector('tbody');
        if (!tbody) return;

        const start = (this.currentPage - 1) * this.options.pageSize;
        const end = start + this.options.pageSize;
        const pageData = this.options.paginate 
            ? this.filteredData.slice(start, end) 
            : this.filteredData;

        // Update row render
        this.renderRows(tbody, pageData);

        // Update pagination
        if (this.options.paginate) {
            this.renderPagination();
        }
    }

    renderRows(tbody, data) {
        // Override in specific implementations
    }

    renderPagination() {
        if (!this.paginationContainer) return;

        const totalPages = Math.ceil(this.filteredData.length / this.options.pageSize);

        let html = `
            <button class="btn btn-sm btn-secondary" 
                ${this.currentPage === 1 ? 'disabled' : ''}
                onclick="table.goToPage(${this.currentPage - 1})">
                ← Prev
            </button>
            <span class="text-muted">Page ${this.currentPage} of ${totalPages}</span>
            <button class="btn btn-sm btn-secondary" 
                ${this.currentPage === totalPages ? 'disabled' : ''}
                onclick="table.goToPage(${this.currentPage + 1})">
                Next →
            </button>
        `;

        this.paginationContainer.innerHTML = html;
    }

    goToPage(page) {
        const totalPages = Math.ceil(this.filteredData.length / this.options.pageSize);
        if (page < 1 || page > totalPages) return;
        this.currentPage = page;
        this.render();
    }
}

// =========================================================
// DATE & NUMBER FORMATTING
// =========================================================
const FormatUtils = {
    date(date, format = 'YYYY-MM-DD') {
        if (!date) return '';
        const d = new Date(date);
        if (isNaN(d.getTime())) return date;

        const pad = (n) => String(n).padStart(2, '0');

        return format
            .replace('YYYY', d.getFullYear())
            .replace('MM', pad(d.getMonth() + 1))
            .replace('DD', pad(d.getDate()))
            .replace('HH', pad(d.getHours()))
            .replace('mm', pad(d.getMinutes()));
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

    number(num, decimals = 0) {
        if (num === null || num === undefined) return '';
        const n = parseFloat(num);
        if (isNaN(n)) return num;
        return n.toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    },

    statusBadge(status) {
        const classes = {
            'draft': 'status-draft',
            'posted': 'status-posted',
            'void': 'status-void',
            'pending': 'status-pending',
            'active': 'status-posted',
            'inactive': 'status-void'
        };

        const className = classes[status.toLowerCase()] || 'status-pending';
        return `<span class="status-badge ${className}">${status}</span>`;
    }
};

// =========================================================
// LOADING STATE
// =========================================================
class LoadingState {
    static show(element, message = 'Loading...') {
        element.style.position = 'relative';
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div style="text-align: center;">
                <div class="spinner" style="width: 40px; height: 40px; margin: 0 auto 12px;"></div>
                <div style="color: var(--gray-600); font-size: 0.9rem;">${message}</div>
            </div>
        `;
        element.appendChild(overlay);
        return overlay;
    }

    static hide(element) {
        const overlay = element.querySelector('.loading-overlay');
        if (overlay) overlay.remove();
    }
}

// =========================================================
// CONFIRMATION DIALOG
// =========================================================
function confirmDialog(message, title = 'Confirm', onConfirm = null) {
    return new Promise((resolve) => {
        const modalId = 'confirm-modal';

        // Remove existing
        const existing = document.getElementById(modalId);
        if (existing) existing.remove();

        // Create modal
        const modalEl = document.createElement('div');
        modalEl.id = modalId;
        modalEl.className = 'modal-overlay';
        modalEl.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h3 class="modal-title">${title}</h3>
                    <button class="modal-close" onclick="modal.close('${modalId}')">×</button>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="modal.close('${modalId}')">Cancel</button>
                    <button class="btn btn-danger" id="confirm-btn">Confirm</button>
                </div>
            </div>
        `;

        document.body.appendChild(modalEl);
        modal.open(modalId);

        document.getElementById('confirm-btn').addEventListener('click', () => {
            modal.close(modalId);
            if (onConfirm) onConfirm();
            resolve(true);
        });

        modalEl.addEventListener('click', (e) => {
            if (e.target === modalEl) {
                modal.close(modalId);
                resolve(false);
            }
        });
    });
}

// =========================================================
// SIDEBAR NAVIGATION
// =========================================================
function initSidebar() {
    const sidebar = document.querySelector('.erp-sidebar');
    const toggle = document.querySelector('.sidebar-toggle');

    if (toggle) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // Highlight active nav
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.getAttribute('href') === currentPage) {
            item.classList.add('active');
        }
    });
}

// =========================================================
// INITIALIZATION
// =========================================================
document.addEventListener('DOMContentLoaded', () => {
    initSidebar();

    // Set company info
    document.querySelectorAll('.company-name').forEach(el => {
        el.textContent = ERP_CONFIG.COMPANY_NAME;
    });

    document.querySelectorAll('.company-tagline').forEach(el => {
        el.textContent = ERP_CONFIG.COMPANY_TAGLINE;
    });

    document.querySelectorAll('.version-number').forEach(el => {
        el.textContent = `v${ERP_CONFIG.VERSION}`;
    });

    // Set current date
    document.querySelectorAll('.current-date').forEach(el => {
        el.textContent = FormatUtils.date(new Date(), 'YYYY-MM-DD');
    });
});

// Export for module usage
window.ERP_CONFIG = ERP_CONFIG;
window.api = api;
window.toast = toast;
window.modal = modal;
window.FormatUtils = FormatUtils;
window.FormUtils = FormUtils;
window.DataTable = DataTable;
window.LoadingState = LoadingState;
window.confirmDialog = confirmDialog;
