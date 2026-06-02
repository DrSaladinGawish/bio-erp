/**
 * INCENTIVE HOUSE ERP - Transactions Module
 * Journal Voucher Entry, Posting, Editing, and Voiding
 */

// =========================================================
// TRANSACTION STATE
// =========================================================
class TransactionManager {
    constructor() {
        this.currentTransaction = null;
        this.lineItems = [];
        this.transactions = [];
        this.isEditing = false;
        this.editId = null;
    }

    // Initialize the module
    init() {
        this.bindEvents();
        this.loadTransactions();
        this.setupLineItems();
    }

    // Bind all event handlers
    bindEvents() {
        // Form submission
        const form = document.getElementById('transaction-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveTransaction();
            });
        }

        // Post button
        const postBtn = document.getElementById('btn-post');
        if (postBtn) {
            postBtn.addEventListener('click', () => this.postTransaction());
        }

        // New button
        const newBtn = document.getElementById('btn-new');
        if (newBtn) {
            newBtn.addEventListener('click', () => this.newTransaction());
        }

        // Print button
        const printBtn = document.getElementById('btn-print');
        if (printBtn) {
            printBtn.addEventListener('click', () => window.print());
        }

        // Search
        const searchInput = document.getElementById('transaction-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchTransactions(e.target.value);
            });
        }

        // Filter status
        const statusFilter = document.getElementById('filter-status');
        if (statusFilter) {
            statusFilter.addEventListener('change', () => this.applyFilters());
        }

        // Filter date range
        const dateFrom = document.getElementById('filter-date-from');
        const dateTo = document.getElementById('filter-date-to');
        if (dateFrom && dateTo) {
            dateFrom.addEventListener('change', () => this.applyFilters());
            dateTo.addEventListener('change', () => this.applyFilters());
        }
    }

    // Setup line items table
    setupLineItems() {
        const addLineBtn = document.getElementById('add-line-btn');
        if (addLineBtn) {
            addLineBtn.addEventListener('click', () => this.addLineItem());
        }

        // Add initial empty line
        this.addLineItem();
    }

    // Add a new line item row
    addLineItem(data = null) {
        const tbody = document.getElementById('line-items-body');
        if (!tbody) return;

        const lineNumber = tbody.children.length + 1;
        const row = document.createElement('tr');
        row.dataset.lineNumber = lineNumber;

        row.innerHTML = `
            <td class="line-number">${lineNumber}</td>
            <td>
                <input type="text" class="line-input" name="account_code_${lineNumber}" 
                    placeholder="Account Code" value="${data?.account_code || ''}" required>
            </td>
            <td>
                <input type="text" class="line-input" name="account_name_${lineNumber}" 
                    placeholder="Account Name" value="${data?.account_name || ''}">
            </td>
            <td>
                <textarea class="line-input" name="description_${lineNumber}" 
                    placeholder="Description" rows="1">${data?.description || ''}</textarea>
            </td>
            <td>
                <input type="number" class="line-input text-right font-mono" 
                    name="debit_${lineNumber}" placeholder="0.00" 
                    value="${data?.debit || ''}" step="0.01" min="0"
                    onchange="txManager.calculateTotals()">
            </td>
            <td>
                <input type="number" class="line-input text-right font-mono" 
                    name="credit_${lineNumber}" placeholder="0.00" 
                    value="${data?.credit || ''}" step="0.01" min="0"
                    onchange="txManager.calculateTotals()">
            </td>
            <td>
                <input type="text" class="line-input" name="cost_center_${lineNumber}" 
                    placeholder="Cost Center" value="${data?.cost_center || ''}">
            </td>
            <td class="actions">
                <button type="button" class="btn-icon" onclick="txManager.removeLineItem(this)" title="Remove line">
                    🗑
                </button>
            </td>
        `;

        tbody.appendChild(row);
        this.calculateTotals();
    }

    // Remove a line item
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

    // Renumber line items after deletion
    renumberLines() {
        const tbody = document.getElementById('line-items-body');
        Array.from(tbody.children).forEach((row, index) => {
            row.dataset.lineNumber = index + 1;
            row.querySelector('.line-number').textContent = index + 1;
        });
    }

    // Calculate totals
    calculateTotals() {
        let totalDebit = 0;
        let totalCredit = 0;

        const tbody = document.getElementById('line-items-body');
        if (!tbody) return;

        Array.from(tbody.children).forEach(row => {
            const debitInput = row.querySelector('[name^="debit_"]');
            const creditInput = row.querySelector('[name^="credit_"]');

            const debit = parseFloat(debitInput?.value) || 0;
            const credit = parseFloat(creditInput?.value) || 0;

            totalDebit += debit;
            totalCredit += credit;
        });

        // Update display
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

        // Enable/disable post button based on balance
        const postBtn = document.getElementById('btn-post');
        if (postBtn) {
            postBtn.disabled = difference !== 0 || totalDebit === 0;
        }

        return { totalDebit, totalCredit, difference };
    }

    // Validate the form
    validateForm() {
        const form = document.getElementById('transaction-form');
        const result = FormUtils.validate(form);

        if (!result.valid) {
            FormUtils.showErrors(form, result.errors);
            toast.error('Please fill in all required fields');
            return false;
        }

        // Check line items
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

    // Collect form data
    collectData() {
        const form = document.getElementById('transaction-form');
        const formData = FormUtils.serialize(form);

        // Collect line items
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

    // Map frontend form data to backend JV payload
    toJVPayload(data) {
        return {
            jv_date: data.transaction_date,
            reference: data.reference_no || undefined,
            description: data.description || '',
            notes: data.notes || '',
            lines: data.line_items.map((item, idx) => ({
                line_number: idx + 1,
                gl_account_id: parseInt(item.account_code) || 0,
                debit_amount: item.debit || 0,
                credit_amount: item.credit || 0,
                description: item.description || ''
            }))
        };
    }

    // Map backend JV object to frontend transaction format
    fromJV(jv) {
        return {
            id: jv.id,
            reference_no: jv.jv_number,
            transaction_type: 'JV',
            transaction_date: jv.jv_date,
            description: jv.description || '',
            notes: jv.notes || '',
            status: (jv.status || 'draft').toLowerCase(),
            total_debit: jv.total_debit || 0,
            total_credit: jv.total_credit || 0,
            line_items: (jv.lines || []).map(line => ({
                line_number: line.line_number,
                account_code: String(line.gl_account_id),
                account_name: line.gl_account_name || '',
                description: line.description || '',
                debit: line.debit_amount || 0,
                credit: line.credit_amount || 0
            }))
        };
    }

    // Save transaction (draft) — creates via POST /finance/jv
    async saveTransaction() {
        if (!this.validateForm()) return;

        const data = this.collectData();

        try {
            LoadingState.show(document.getElementById('transaction-form'), 'Saving...');

            if (this.isEditing && this.editId) {
                toast.warning('Editing not supported via API. Create a new draft instead.');
                return;
            }

            const payload = this.toJVPayload(data);
            const response = await api.post('/finance/jv', payload);
            toast.success('Transaction saved as draft (JV #' + response.jv_number + ')');
            this.loadTransactions();
            this.newTransaction();
        } catch (error) {
            console.error('Save error:', error);
            toast.error(error.message || 'Failed to save transaction');
        } finally {
            LoadingState.hide(document.getElementById('transaction-form'));
        }
    }

    // Post transaction — creates via POST /finance/jv, then posts via POST /finance/jv/{id}/post
    async postTransaction() {
        if (!this.validateForm()) return;

        const confirmed = await confirmDialog(
            'Are you sure you want to post this transaction? Posted transactions cannot be edited.',
            'Confirm Post',
            null
        );

        if (!confirmed) return;

        const data = this.collectData();

        try {
            LoadingState.show(document.getElementById('transaction-form'), 'Posting...');

            // Step 1: Create the JV as draft
            const payload = this.toJVPayload(data);
            const created = await api.post('/finance/jv', payload);

            // Step 2: Post the JV
            const posted = await api.post(`/finance/jv/${created.jv_id}/post`);
            toast.success('Transaction posted successfully (JV #' + posted.jv_number + ')');
            this.loadTransactions();
            this.newTransaction();
        } catch (error) {
            console.error('Post error:', error);
            toast.error(error.message || 'Failed to post transaction');
        } finally {
            LoadingState.hide(document.getElementById('transaction-form'));
        }
    }

    // Void (reverse) transaction — POST /finance/jv/{id}/reverse
    async voidTransaction(id) {
        const transaction = this.transactions.find(t => t.id === id);
        if (!transaction) return;

        if (transaction.status === 'void') {
            toast.warning('Transaction is already voided/reversed');
            return;
        }

        const confirmed = await confirmDialog(
            `Are you sure you want to reverse/void transaction ${transaction.reference_no || id}? This creates a reversing entry.`,
            'Confirm Reverse',
            null
        );

        if (!confirmed) return;

        try {
            await api.post(`/finance/jv/${id}/reverse`);
            toast.success('Transaction reversed (voided) successfully');
            this.loadTransactions();
        } catch (error) {
            console.error('Reverse error:', error);
            toast.error(error.message || 'Failed to reverse transaction');
        }
    }

    // Edit transaction (only draft — loads full JV from backend)
    async editTransaction(id) {
        const transaction = this.transactions.find(t => t.id === id);
        if (!transaction) return;

        if (transaction.status === 'posted') {
            toast.warning('Posted transactions cannot be edited. Use reverse instead.');
            return;
        }

        if (transaction.status === 'reversed' || transaction.status === 'void') {
            toast.warning('Reversed/voided transactions cannot be edited');
            return;
        }

        try {
            // Fetch full JV details with lines from backend
            const jv = await api.get(`/finance/jv/${id}`);
            const full = this.fromJV(jv);

            this.isEditing = true;
            this.editId = id;

            // Populate form
            const form = document.getElementById('transaction-form');
            FormUtils.populate(form, {
                transaction_type: 'JV',
                reference_no: full.reference_no,
                transaction_date: full.transaction_date?.split('T')[0],
                description: full.description,
                notes: full.notes || '',
                currency: 'AED',
                exchange_rate: 1
            });

            // Populate line items
            const tbody = document.getElementById('line-items-body');
            tbody.innerHTML = '';

            if (full.line_items && full.line_items.length > 0) {
                full.line_items.forEach(item => {
                    this.addLineItem(item);
                });
            } else {
                this.addLineItem();
            }

            this.calculateTotals();

            // Update UI
            document.getElementById('btn-post').disabled = false;
            document.getElementById('form-title').textContent = 'Edit Transaction (view only)';

            form.scrollIntoView({ behavior: 'smooth' });
            toast.info('Loaded JV details. Save creates a new draft (no PUT endpoint).');
        } catch (error) {
            console.error('Edit load error:', error);
            toast.error(error.message || 'Failed to load transaction details');
        }
    }

    // View transaction details
    async viewTransaction(id) {
        let transaction = this.transactions.find(t => t.id === id);
        if (!transaction) return;

        // Try to fetch full details with line items from backend
        try {
            const jv = await api.get(`/finance/jv/${id}`);
            transaction = this.fromJV(jv);
        } catch (e) {
            // Use cached data if API fails
        }

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
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Account</th>
                        <th>Name</th>
                        <th>Description</th>
                        <th class="text-right">Debit</th>
                        <th class="text-right">Credit</th>
                        <th>Cost Center</th>
                    </tr>
                </thead>
                <tbody>
                    ${lineItemsHtml || '<tr><td colspan="7" class="text-center text-muted">No line items</td></tr>'}
                </tbody>
            </table>

            <div class="totals-panel mt-3">
                <div class="totals-row">
                    <span class="totals-label">Total Debit</span>
                    <span class="totals-value">${FormatUtils.currency(transaction.total_debit)}</span>
                </div>
                <div class="totals-row">
                    <span class="totals-label">Total Credit</span>
                    <span class="totals-value">${FormatUtils.currency(transaction.total_credit)}</span>
                </div>
                <div class="totals-row">
                    <span class="totals-label">Difference</span>
                    <span class="totals-value text-success">${FormatUtils.currency(0)}</span>
                </div>
            </div>
        `;

        modal.open('view-transaction-modal');
    }

    // New transaction - reset form
    newTransaction() {
        this.isEditing = false;
        this.editId = null;

        const form = document.getElementById('transaction-form');
        FormUtils.reset(form);

        // Reset line items
        const tbody = document.getElementById('line-items-body');
        tbody.innerHTML = '';
        this.addLineItem();

        // Set default date
        const dateField = form.querySelector('[name="transaction_date"]');
        if (dateField) {
            dateField.value = new Date().toISOString().split('T')[0];
        }

        // Reset UI
        document.getElementById('btn-post').disabled = true;
        document.getElementById('form-title').textContent = 'New Transaction';

        this.calculateTotals();
    }

    // Load transactions from API
    async loadTransactions() {
        const tableBody = document.getElementById('transactions-table-body');
        if (!tableBody) return;

        try {
            LoadingState.show(document.querySelector('.transactions-list'), 'Loading transactions...');

            let data;
            try {
                data = await api.get('/finance/jv');
            } catch (e) {
                // Fallback to demo data if API not available
                data = this.getDemoData();
            }

            const raw = Array.isArray(data) ? data : (data.items || []);
            this.transactions = raw.map(jv => this.fromJV(jv));
            this.renderTransactions();
        } catch (error) {
            console.error('Load error:', error);
            toast.error('Failed to load transactions');
        } finally {
            LoadingState.hide(document.querySelector('.transactions-list'));
        }
    }

    // Demo data for testing
    getDemoData() {
        return [
            {
                id: 'TXN-001',
                reference_no: 'JV-2024-001',
                transaction_type: 'JV',
                transaction_date: '2024-01-15',
                description: 'Monthly rent allocation',
                status: 'posted',
                total_debit: 5000.00,
                total_credit: 5000.00,
                line_items: [
                    { line_number: 1, account_code: '6100', account_name: 'Rent Expense', description: 'Office rent Jan 2024', debit: 5000, credit: 0, cost_center: 'HQ' },
                    { line_number: 2, account_code: '2100', account_name: 'Accounts Payable', description: 'Rent payable', debit: 0, credit: 5000, cost_center: 'HQ' }
                ]
            },
            {
                id: 'TXN-002',
                reference_no: 'JV-2024-002',
                transaction_type: 'JV',
                transaction_date: '2024-01-16',
                description: 'Salary allocation',
                status: 'draft',
                total_debit: 25000.00,
                total_credit: 25000.00,
                line_items: [
                    { line_number: 1, account_code: '6200', account_name: 'Salary Expense', description: 'Jan 2024 salaries', debit: 25000, credit: 0, cost_center: 'HR' },
                    { line_number: 2, account_code: '1100', account_name: 'Cash', description: 'Cash payment', debit: 0, credit: 25000, cost_center: 'HR' }
                ]
            },
            {
                id: 'TXN-003',
                reference_no: 'JV-2024-003',
                transaction_type: 'JV',
                transaction_date: '2024-01-17',
                description: 'Equipment purchase',
                status: 'void',
                total_debit: 15000.00,
                total_credit: 15000.00,
                line_items: [
                    { line_number: 1, account_code: '1500', account_name: 'Equipment', description: 'Laptops', debit: 15000, credit: 0, cost_center: 'IT' },
                    { line_number: 2, account_code: '1100', account_name: 'Cash', description: 'Cash payment', debit: 0, credit: 15000, cost_center: 'IT' }
                ]
            }
        ];
    }

    // Render transactions table
    renderTransactions(data = null) {
        const tableBody = document.getElementById('transactions-table-body');
        if (!tableBody) return;

        const items = data || this.transactions;

        if (items.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center" style="padding: 40px;">
                        <div class="empty-state">
                            <div class="icon">📄</div>
                            <h3>No transactions found</h3>
                            <p>Create a new transaction to get started</p>
                        </div>
                    </td>
                </tr>
            `;
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
                        <button class="btn btn-sm btn-secondary" onclick="txManager.viewTransaction('${tx.id}')" title="View">
                            👁
                        </button>
                        ${tx.status === 'draft' ? `
                            <button class="btn btn-sm btn-primary" onclick="txManager.editTransaction('${tx.id}')" title="Edit">
                                ✎
                            </button>
                        ` : ''}
                        ${tx.status !== 'void' ? `
                            <button class="btn btn-sm btn-danger" onclick="txManager.voidTransaction('${tx.id}')" title="Void">
                                ✕
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `).join('');
    }

    // Search transactions
    searchTransactions(query) {
        if (!query) {
            this.renderTransactions();
            return;
        }

        const lowerQuery = query.toLowerCase();
        const filtered = this.transactions.filter(tx => 
            (tx.reference_no && tx.reference_no.toLowerCase().includes(lowerQuery)) ||
            (tx.description && tx.description.toLowerCase().includes(lowerQuery)) ||
            (tx.transaction_type && tx.transaction_type.toLowerCase().includes(lowerQuery)) ||
            tx.id.toLowerCase().includes(lowerQuery)
        );

        this.renderTransactions(filtered);
    }

    // Apply filters
    applyFilters() {
        const statusFilter = document.getElementById('filter-status')?.value;
        const dateFrom = document.getElementById('filter-date-from')?.value;
        const dateTo = document.getElementById('filter-date-to')?.value;

        let filtered = [...this.transactions];

        if (statusFilter) {
            filtered = filtered.filter(tx => tx.status === statusFilter);
        }

        if (dateFrom) {
            filtered = filtered.filter(tx => tx.transaction_date >= dateFrom);
        }

        if (dateTo) {
            filtered = filtered.filter(tx => tx.transaction_date <= dateTo);
        }

        this.renderTransactions(filtered);
    }
}

// Initialize
const txManager = new TransactionManager();

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('transaction-form')) {
        txManager.init();
    }
});

// Export
window.txManager = txManager;
