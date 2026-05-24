document.addEventListener('DOMContentLoaded', function() {
    // HTMX toast/notification handler
    document.body.addEventListener('htmx:responseError', function(evt) {
        console.error('HTMX error:', evt.detail.status, evt.detail.statusText);
    });

    document.body.addEventListener('htmx:sendError', function(evt) {
        console.error('HTMX send error:', evt.detail);
    });

    // Export button
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            const table = document.querySelector('.table');
            if (!table) return;
            let csv = [];
            const rows = table.querySelectorAll('tr');
            for (const row of rows) {
                const cols = row.querySelectorAll('td, th');
                const vals = Array.from(cols).map(c => '"' + c.innerText.trim().replace(/"/g, '""') + '"');
                csv.push(vals.join(','));
            }
            const blob = new Blob([csv.join('\n')], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'ledger_export.csv';
            a.click();
            URL.revokeObjectURL(url);
        });
    }

    // Logout
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            document.cookie = 'access_token=; Max-Age=0; path=/';
            window.location.reload();
        });
    }
});
