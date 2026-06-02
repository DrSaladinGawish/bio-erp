/**
 * P4 TRANSACTIONS MODULE - Live API Integration
 * Connects transaction forms to real BIO-ERP endpoints
 */

class TransactionManager {
    constructor() {
        this.currentTransaction = null;
        this.lineItems = [];
        this.transactions = [];
        this.isEditing = false;
        this.editId = null;
        this.autoRefreshInterval = null;
    }

    init() {
        this.bindEvents();
        this.loadTransactions();
        this.setupLineItems();
        this.setupAutoRefresh();
    }

    setupAutoRefresh() {
        if (ERP_CONFIG.FEATURES.auto_refresh && ERP_CONFIG.FEATURES.real_api) {
            this.autoRefreshInterval = setInterval(() => {
                this.loadTransactions(true);  // silent refresh
            }, ERP_CONFIG.FEATURES.refresh_interval);
        }
    }

    bindEvents() {
        const form = document.getElementById('transaction-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveTransaction();
            });
        }

        const postBtn = document.getElementById('btn-post');
        if (postBtn) postBtn.addEventListener('click', () => this.postTransaction());

        const newBtn = document.getElementById('btn-new');
        if (newBtn) newBtn.addEventListener('click', () => this.newTransaction());

        const printBtn = document.getElementById('btn-print');
        if (printBtn) printBtn.addEventListener('click', () => window.print());

        const searchInput = document.getElementById('transaction-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.searchTransactions(e.target.value));
        }

        ['filter-status', 'filter-date-from', 'filter-date-to'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', () => this.applyFilters());
        });
    }

    setupLineItems() {
        const addLineBtn = document.getElementById('add-line-btn');
        if (addLineBtn) addLineBtn.addEventListener('click', () => this.addLineItem());
        this.addLineItem();
    }

    addLineItem(data = null) {
        const tbody = document.getElementById('line-items-body');
        if (!tbody) return;
        const lineNumber = tbody.children.length + 1;
        const row = document.createElement('tr');
        row.dataset.lineNumber = lineNumber;

        row.innerHTML = `
            <td class="line-number">${lineNumber}</td>
            <td><input type="text" class="line-input" name="account_code_${lineNumber}" 
                placeholder="Account Code" value="${data?.account_code || ''}" required></td>
            <td><input type="text" class="line-input" name="account_name_${lineNumber}" 
                placeholder="Account Name" value="${data?.account_name || ''}"></td>
            <td><textarea class="line-input" name="description_${lineNumber}" 
                placeholder="Description" rows="1">${data?.description || ''}</textarea></td>
            <td><input type="number" class="line-input text-right font-mono" 
                name="debit_${lineNumber}" placeholder="0.00" 
                value="${data?.debit || ''}" step="0.01" min="0"
                onchange="txManager.calculateTotals()"></td>
            <td><input type="number" class="line-input text-right font-mono" 
                name="credit_${lineNumber}" placeholder="0.00" 
                value="${data?.credit || ''}" step="0.01" min="0"
                onchange="txManager.calculateTotals()"></td>
            <td><input type="text" class="line-input" name="cost_center_${lineNumber}" 
                placeholder="Cost Center" value="${data?.cost_center || ''}"></td>
            <td class="actions">
                <button type="button" class="btn-icon" onclick="txManager.removeLineItem(this)" title="Remove">🗑</button>
            </td>`;
        tbody.appendChild(row);
        this.calculateTotals();
    }

    removeLineItem(btn) {
        const tbody = document.getElementById('line-items-body');
        if (tbody.children.length <= 1) {
            toast.warning('At least one line item is required');
            return;
        }
        btn.closest('tr').remove();
        this.renumberLines();
        this.calculateTotals();
    }

    renumberLines() {
        const tbody = document.getElementById('line-items-body');
        Array.from(tbody.children).forEach((row, index) => {
            row.dataset.lineNumber = index + 1;
            row.querySelector('.line-number').textContent = index + 1;
        });
    }

    calculateTotals() {
        let totalDebit = 0, totalCredit = 0;
        const tbody = document.getElementById('line-items-body');
        if (!tbody) return;

        Array.from(tbody.children).forEach(row => {
            const debit = parseFloat(row.querySelector('[name^="debit_"]')?.value) || 0;
            const credit = parseFloat(row.querySelector('[name^="credit_"]')?.value) || 0;
            totalDebit += debit;
            totalCredit += credit;
        });

        const totalDebitEl = document.getElementById('total-debit');
        const totalCreditEl = document.getElementById('total-credit');
        const differenceEl = document.getElementById('total-difference');

        if (totalDebitEl) totalDebitEl.textContent = FormatUtils.currency(totalDebit);
        if (totalCreditEl) totalCreditEl.textContent = FormatUtils.currency(totalCredit);

        const difference = totalDebit - totalCredit;
        if (differenceEl) {
            differenceEl.textContent = FormatUtils.currency(Math.abs(difference));
            differenceEl.className = difference === 0 ? 'totals-value text-success' : 'totals-value text-danger';
        }

        const postBtn = document.getElementById('btn-post');
        if (postBtn) postBtn.disabled = difference !== 0 || totalDebit === 0;

        return { totalDebit, totalCredit, difference };
    }

    validateForm() {
        const form = document.getElementById('transaction-form');
        const result = FormUtils.validate(form);
        if (!result.valid) {
            toast.error('Please fill in all required fields');
            return false;
        }
        const totals = this.calculateTotals();
        if (totals.difference !== 0) {
            toast.error('Debits and credits must balance');
            return false;
        }
        if (totals.totalDebit === 0) {
            toast.error('Transaction must have at least one line item with a value');
            return false;
        }
        return true;
    }

    collectData() {
        const form = document.getElementById('transaction-form');
        const formData = FormUtils.serialize(form);
        const lineItems = [];
        const tbody = document.getElementById('line-items-body');

        Array.from(tbody.children).forEach(row => {
            const lineNum = row.dataset.lineNumber;
            const debit = parseFloat(row.querySelector(`[name="debit_${lineNum}"]`)?.value) || 0;
            const credit = parseFloat(row.querySelector(`[name="credit_${lineNum}"]`)?.value) || 0;
            if (debit > 0 || credit > 0) {
                lineItems.push({
                    line_number: parseInt(lineNum),
                    account_code: row.querySelector(`[name="account_code_${lineNum}"]`)?.value || '',
                    account_name: row.querySelector(`[name="account_name_${lineNum}"]`)?.value || '',
                    description: row.querySelector(`[name="description_${lineNum}"]`)?.value || '',
                    debit: debit,
                    credit: credit,
                    cost_center: row.querySelector(`[name="cost_center_${lineNum}"]`)?.value || ''
                });
            }
        });

        return {
            transaction_type: formData.transaction_type || 'JV',
            reference_no: formData.reference_no || '',
            transaction_date: formData.transaction_date,
            description: formData.description || '',
            notes: formData.notes || '',
            currency: formData.currency || 'USD',
            exchange_rate: parseFloat(formData.exchange_rate) || 1,
            line_items: lineItems,
            total_debit: lineItems.reduce((sum, li) => sum + li.debit, 0),
            total_credit: lineItems.reduce((sum, li) => sum + li.credit, 0)
        };
    }

    async saveTransaction() {
        if (!this.validateForm()) return;
        const data = this.collectData();
        data.status = 'draft';

        try {
            LoadingState.show(document.getElementById('transaction-form'), 'Saving...');
            let response;
            if (this.isEditing && this.editId) {
                response = await api.put(`/transactions/${this.editId}`, data);
                toast.success('Transaction updated successfully');
            } else {
                response = await api.post('/transactions', data);
                toast.success('Transaction saved as draft');
            }
            this.loadTransactions();
            if (!this.isEditing) this.newTransaction();
        } catch (error) {
            console.error('Save error:', error);
            if (error.status === 0) {
                toast.error('Cannot connect to server. Using demo mode.');
                this.fallbackSave(data);
            } else {
                toast.error(error.message || 'Failed to save transaction');
            }
        } finally {
            LoadingState.hide(document.getElementById('transaction-form'));
        }
    }

    async postTransaction() {
        if (!this.validateForm()) return;
        const confirmed = await confirmDialog(
            'Are you sure you want to post this transaction? Posted transactions cannot be edited.',
            'Confirm Post'
        );
        if (!confirmed) return;

        const data = this.collectData();
        data.status = 'posted';

        try {
            LoadingState.show(document.getElementById('transaction-form'), 'Posting...');
            let response;
            if (this.isEditing && this.editId) {
                response = await api.put(`/transactions/${this.editId}`, data);
            } else {
                response = await api.post('/transactions', data);
            }
            toast.success('Transaction posted successfully');
            this.loadTransactions();
            this.newTransaction();
        } catch (error) {
            console.error('Post error:', error);
            toast.error(error.message || 'Failed to post transaction');
        } finally {
            LoadingState.hide(document.getElementById('transaction-form'));
        }
    }

    async voidTransaction(id) {
        const transaction = this.transactions.find(t => t.id === id);
        if (!transaction) return;
        if (transaction.status === 'void') {
            toast.warning('Transaction is already voided');
            return;
        }
        const confirmed = await confirmDialog(
            `Void transaction ${transaction.reference_no || id}? This cannot be undone.`,
            'Confirm Void'
        );
        if (!confirmed) return;

        try {
            await api.patch(`/transactions/${id}/void`, { reason: 'User voided' });
            toast.success('Transaction voided successfully');
            this.loadTransactions();
        } catch (error) {
            console.error('Void error:', error);
            toast.error(error.message || 'Failed to void transaction');
        }
    }

    editTransaction(id) {
        const transaction = this.transactions.find(t => t.id === id);
        if (!transaction) return;
        if (transaction.status === 'posted') {
            toast.warning('Posted transactions cannot be edited. Use reverse instead.');
            return;
        }
        if (transaction.status === 'void') {
            toast.warning('Voided transactions cannot be edited');
            return;
        }

        this.isEditing = true;
        this.editId = id;
        const form = document.getElementById('transaction-form');
        FormUtils.populate(form, {
            transaction_type: transaction.transaction_type,
            reference_no: transaction.reference_no,
            transaction_date: transaction.transaction_date?.split('T')[0],
            description: transaction.description,
            notes: transaction.notes,
            currency: transaction.currency,
            exchange_rate: transaction.exchange_rate
        });

        const tbody = document.getElementById('line-items-body');
        tbody.innerHTML = '';
        if (transaction.line_items && transaction.line_items.length > 0) {
            transaction.line_items.forEach(item => this.addLineItem(item));
        } else {
            this.addLineItem();
        }
        this.calculateTotals();
        document.getElementById('btn-post').disabled = false;
        document.getElementById('form-title').textContent = 'Edit Transaction';
        form.scrollIntoView({ behavior: 'smooth' });
        toast.info('Editing transaction. Save when done.');
    }

    viewTransaction(id) {
        const transaction = this.transactions.find(t => t.id === id);
        if (!transaction) return;
        const modalBody = document.getElementById('view-modal-body');
        if (!modalBody) return;

        const lineItemsHtml = (transaction.line_items || []).map(item => `
            <tr>
                <td>${item.line_number}</td>
                <td>${item.account_code}</td>
                <td>${item.account_name}</td>
                <td>${item.description || '-'}</td>
                <td class="text-right font-mono">${item.debit > 0 ? FormatUtils.currency(item.debit) : '-'}</td>
                <td class="text-right font-mono">${item.credit > 0 ? FormatUtils.currency(item.credit) : '-'}</td>
                <td>${item.cost_center || '-'}</td>
            </tr>
        `).join('');

        modalBody.innerHTML = `
            <div class="grid-2 mb-3">
                <div>
                    <div class="form-group">
                        <label class="form-label">Reference No</label>
                        <div class="form-control" style="background: var(--gray-50);">${transaction.reference_no || '-'}</div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Date</label>
                        <div class="form-control" style="background: var(--gray-50);">${FormatUtils.date(transaction.transaction_date)}</div>
                    </div>
                </div>
                <div>
                    <div class="form-group">
                        <label class="form-label">Type</label>
                        <div class="form-control" style="background: var(--gray-50);">${transaction.transaction_type}</div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Status</label>
                        <div>${FormatUtils.statusBadge(transaction.status)}</div>
                    </div>
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Description</label>
                <div class="form-control" style="background: var(--gray-50); min-height: 60px;">${transaction.description || '-'}</div>
            </div>
            <h4 style="margin: 20px 0 12px; color: var(--primary);">Line Items</h4>
            <table class="data-table">
                <thead><tr><th>#</th><th>Account</th><th>Name</th><th>Description</th><th class="text-right">Debit</th><th class="text-right">Credit</th><th>Cost Center</th></tr></thead>
                <tbody>${lineItemsHtml || '<tr><td colspan="7" class="text-center text-muted">No line items</td></tr>'}</tbody>
            </table>
            <div class="totals-panel mt-3">
                <div class="totals-row"><span class="totals-label">Total Debit</span><span class="totals-value">${FormatUtils.currency(transaction.total_debit)}</span></div>
                <div class="totals-row"><span class="totals-label">Total Credit</span><span class="totals-value">${FormatUtils.currency(transaction.total_credit)}</span></div>
                <div class="totals-row"><span class="totals-label">Difference</span><span class="totals-value text-success">${FormatUtils.currency(0)}</span></div>
            </div>`;
        modal.open('view-transaction-modal');
    }

    newTransaction() {
        this.isEditing = false;
        this.editId = null;
        const form = document.getElementById('transaction-form');
        FormUtils.reset(form);
        const tbody = document.getElementById('line-items-body');
        tbody.innerHTML = '';
        this.addLineItem();
        const dateField = form.querySelector('[name="transaction_date"]');
        if (dateField) dateField.value = new Date().toISOString().split('T')[0];
        document.getElementById('btn-post').disabled = true;
        document.getElementById('form-title').textContent = 'New Transaction';
        this.calculateTotals();
    }

    async loadTransactions(silent = false) {
        const tableBody = document.getElementById('transactions-table-body');
        if (!tableBody) return;

        try {
            if (!silent) LoadingState.show(document.querySelector('.transactions-list'), 'Loading transactions...');

            let data;
            if (ERP_CONFIG.FEATURES.real_api) {
                try {
                    data = await api.get('/transactions');
                } catch (e) {
                    if (e.status === 0) {
                        toast.warning('API server offline. Switching to demo data.');
                    }
                    data = this.getDemoData();
                }
            } else {
                data = this.getDemoData();
            }

            this.transactions = Array.isArray(data) ? data : (data.items || []);
            this.renderTransactions();
        } catch (error) {
            console.error('Load error:', error);
            if (!silent) toast.error('Failed to load transactions');
        } finally {
            if (!silent) LoadingState.hide(document.querySelector('.transactions-list'));
        }
    }

    getDemoData() {
        return [
            {
                id: 'TXN-001', reference_no: 'JV-2024-001', transaction_type: 'JV',
                transaction_date: '2024-01-15', description: 'Monthly rent allocation',
                status: 'posted', total_debit: 5000.00, total_credit: 5000.00,
                line_items: [
                    { line_number: 1, account_code: '6100', account_name: 'Rent Expense', description: 'Office rent Jan 2024', debit: 5000, credit: 0, cost_center: 'HQ' },
                    { line_number: 2, account_code: '2100', account_name: 'Accounts Payable', description: 'Rent payable', debit: 0, credit: 5000, cost_center: 'HQ' }
                ]
            },
            {
                id: 'TXN-002', reference_no: 'JV-2024-002', transaction_type: 'JV',
                transaction_date: '2024-01-16', description: 'Salary allocation',
                status: 'draft', total_debit: 25000.00, total_credit: 25000.00,
                line_items: [
                    { line_number: 1, account_code: '6200', account_name: 'Salary Expense', description: 'Jan 2024 salaries', debit: 25000, credit: 0, cost_center: 'HR' },
                    { line_number: 2, account_code: '1100', account_name: 'Cash', description: 'Cash payment', debit: 0, credit: 25000, cost_center: 'HR' }
                ]
            },
            {
                id: 'TXN-003', reference_no: 'JV-2024-003', transaction_type: 'JV',
                transaction_date: '2024-01-17', description: 'Equipment purchase',
                status: 'void', total_debit: 15000.00, total_credit: 15000.00,
                line_items: [
                    { line_number: 1, account_code: '1500', account_name: 'Equipment', description: 'Laptops', debit: 15000, credit: 0, cost_center: 'IT' },
                    { line_number: 2, account_code: '1100', account_name: 'Cash', description: 'Cash payment', debit: 0, credit: 15000, cost_center: 'IT' }
                ]
            }
        ];
    }

    renderTransactions(data = null) {
        const tableBody = document.getElementById('transactions-table-body');
        if (!tableBody) return;
        const items = data || this.transactions;

        if (items.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="8" class="text-center" style="padding: 40px;"><div class="empty-state"><div class="icon">📄</div><h3>No transactions found</h3><p>Create a new transaction to get started</p></div></td></tr>`;
            return;
        }

        tableBody.innerHTML = items.map(tx => `
            <tr>
                <td><strong>${tx.reference_no || tx.id}</strong></td>
                <td>${tx.transaction_type}</td>
                <td>${FormatUtils.date(tx.transaction_date)}</td>
                <td>${tx.description || '-'}</td>
                <td class="text-right font-mono">${FormatUtils.currency(tx.total_debit)}</td>
                <td class="text-right font-mono">${FormatUtils.currency(tx.total_credit)}</td>
                <td>${FormatUtils.statusBadge(tx.status)}</td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-secondary" onclick="txManager.viewTransaction('${tx.id}')" title="View">👁</button>
                        ${tx.status === 'draft' ? `<button class="btn btn-sm btn-primary" onclick="txManager.editTransaction('${tx.id}')" title="Edit">✎</button>` : ''}
                        ${tx.status !== 'void' ? `<button class="btn btn-sm btn-danger" onclick="txManager.voidTransaction('${tx.id}')" title="Void">✕</button>` : ''}
                    </div>
                </td>
            </tr>
        `).join('');
    }

    searchTransactions(query) {
        if (!query) { this.renderTransactions(); return; }
        const lowerQuery = query.toLowerCase();
        const filtered = this.transactions.filter(tx => 
            (tx.reference_no && tx.reference_no.toLowerCase().includes(lowerQuery)) ||
            (tx.description && tx.description.toLowerCase().includes(lowerQuery)) ||
            (tx.transaction_type && tx.transaction_type.toLowerCase().includes(lowerQuery)) ||
            tx.id.toLowerCase().includes(lowerQuery)
        );
        this.renderTransactions(filtered);
    }

    applyFilters() {
        const statusFilter = document.getElementById('filter-status')?.value;
        const dateFrom = document.getElementById('filter-date-from')?.value;
        const dateTo = document.getElementById('filter-date-to')?.value;
        let filtered = [...this.transactions];
        if (statusFilter) filtered = filtered.filter(tx => tx.status === statusFilter);
        if (dateFrom) filtered = filtered.filter(tx => tx.transaction_date >= dateFrom);
        if (dateTo) filtered = filtered.filter(tx => tx.transaction_date <= dateTo);
        this.renderTransactions(filtered);
    }

    fallbackSave(data) {
        // Demo mode: save to local array
        const newTx = {
            id: `TXN-${String(this.transactions.length + 1).padStart(3, '0')}`,
            ...data,
            transaction_date: data.transaction_date || new Date().toISOString().split('T')[0]
        };
        this.transactions.unshift(newTx);
        this.renderTransactions();
        this.newTransaction();
    }
}

const txManager = new TransactionManager();
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('transaction-form')) txManager.init();
});
window.txManager = txManager;
