import { useState } from 'react';

const reports = [
  { icon: '📈', title: 'P&L Statement', desc: 'Profit and loss summary across all active brains with period-over-period comparison' },
  { icon: '📋', title: 'Balance Sheet', desc: 'Consolidated balance sheet with asset, liability, and equity breakdown by brain' },
  { icon: '💵', title: 'Cash Flow', desc: 'Operating, investing, and financing cash flow analysis with 30-day forecast' },
  { icon: '📅', title: 'AR/AP Aging', desc: 'Receivables and payables aging report with overdue item escalation' },
  { icon: '📊', title: 'Revenue by Organ', desc: 'Revenue contribution analysis per organ with trend and variance' },
  { icon: '🎯', title: 'Budget vs Actual', desc: 'Budget variance analysis with YTD performance and forecast adjustment' },
];

export function FinancialChamber() {
  const [generating, setGenerating] = useState<string | null>(null);

  const handleGenerate = (id: string) => {
    setGenerating(id);
    setTimeout(() => setGenerating(null), 2000);
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border-t-4 border-green-500 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">💰 FINANCIAL REPORTS</h3>
      </div>
      <div className="divide-y divide-slate-100 dark:divide-slate-700">
        {reports.map((r, i) => (
          <div key={i} className="px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
            <div className="flex items-start gap-3">
              <span className="text-lg mt-0.5">{r.icon}</span>
              <div className="flex-1 min-w-0">
                <h4 className="text-xs font-semibold text-slate-700 dark:text-slate-200">{r.title}</h4>
                <p className="text-[10px] text-slate-400 mt-0.5 leading-relaxed">{r.desc}</p>
              </div>
              <button
                onClick={() => handleGenerate(`fin-${i}`)}
                disabled={generating === `fin-${i}`}
                className={`flex-shrink-0 px-3 py-1.5 text-[10px] font-medium rounded-md transition-all ${
                  generating === `fin-${i}`
                    ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 animate-neural-pulse'
                    : 'bg-green-600 hover:bg-green-500 text-white'
                }`}
              >
                {generating === `fin-${i}` ? 'Generating...' : 'Generate'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
