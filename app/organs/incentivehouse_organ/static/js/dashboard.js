// IHE-ERP v2.4 - Dashboard JS
// Loads live data from /api/dashboard/data and renders Chart.js charts.
(function(){
  function fmtEgp(v){
    return 'EGP ' + (Number(v)||0).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
  }
  function loadDashboard(range){
    fetch('/api/dashboard/data?range=' + encodeURIComponent(range))
      .then(function(r){ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
      .then(function(d){
        var r = document.getElementById('kpi-revenue'); if(r) r.textContent = fmtEgp(d.total_revenue);
        var e = document.getElementById('kpi-expenses'); if(e) e.textContent = fmtEgp(d.total_expenses);
        var p = document.getElementById('kpi-profit'); if(p) p.textContent = fmtEgp(d.net_profit);
        var pn = document.getElementById('kpi-pnrs'); if(pn) pn.textContent = d.active_pnrs;
        var b = document.getElementById('kpi-bank'); if(b) b.textContent = fmtEgp(d.bank_balance);
        var pi = document.getElementById('kpi-pending'); if(pi) pi.textContent = d.pending_invoices;
        if (window.Chart) renderCharts(d);
      })
      .catch(function(err){ console.error('Dashboard load failed:', err); });
  }
  function renderCharts(d){
    var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    var r = document.getElementById('revenueChart');
    if (r && window.Chart) {
      new Chart(r.getContext('2d'), {
        type: 'line',
        data: { labels: months, datasets: [{
          label: 'Revenue', data: d.revenue_by_month,
          borderColor: '#2d8a8a', backgroundColor: 'rgba(45,138,138,0.15)',
          fill: true, tension: 0.4
        }]},
        options: { responsive: true, maintainAspectRatio: false,
          plugins: { title: { display: true, text: 'Monthly Revenue' } } }
      });
    }
    var e = document.getElementById('expenseChart');
    if (e && window.Chart) {
      new Chart(e.getContext('2d'), {
        type: 'bar',
        data: { labels: months, datasets: [{
          label: 'Expenses', data: d.expenses_by_month, backgroundColor: '#c9a227'
        }]},
        options: { responsive: true, maintainAspectRatio: false,
          plugins: { title: { display: true, text: 'Monthly Expenses' } } }
      });
    }
    var cf = document.getElementById('cashflowChart');
    if (cf && window.Chart) {
      var net = d.revenue_by_month.map(function(r,i){ return (r||0) - (d.expenses_by_month[i]||0); });
      new Chart(cf.getContext('2d'), {
        type: 'line',
        data: { labels: months, datasets: [{
          label: 'Net Cashflow', data: net,
          borderColor: '#1a3a5c', backgroundColor: 'rgba(45,138,138,0.25)',
          fill: true, tension: 0.4
        }]},
        options: { responsive: true, maintainAspectRatio: false,
          plugins: { title: { display: true, text: 'Net Cashflow' } } }
      });
    }
  }
  // Wire range buttons (live if present)
  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('.range-btn').forEach(function(btn){
      btn.addEventListener('click', function(){
        document.querySelectorAll('.range-btn').forEach(function(b){ b.classList.remove('active'); });
        btn.classList.add('active');
        loadDashboard(btn.dataset.range || 'YTD');
      });
    });
    loadDashboard('YTD');
  });
})();
