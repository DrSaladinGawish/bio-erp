import { useState } from 'react';

const reports = [
  { icon: '📦', title: 'Procurement Analysis', desc: 'Deep dive into procurement cycle times, vendor lead times, and cost trends across all organs' },
  { icon: '🏭', title: 'Vendor Performance', desc: 'Scorecard for vendor delivery accuracy, quality metrics, and pricing competitiveness' },
  { icon: '📊', title: 'Inventory Turnover', desc: 'Inventory velocity analysis with slow-mover identification and carrying cost breakdown' },
  { icon: '🚚', title: 'Order Fulfillment Rate', desc: 'End-to-end order-to-delivery metrics with bottleneck detection' },
  { icon: '💰', title: 'Supply Chain Costing', desc: 'Total landed cost analysis including procurement, storage, and distribution' },
];

export function SCMChamber() {
  const [generating, setGenerating] = useState<string | null>(null);

  const handleGenerate = (id: string) => {
    setGenerating(id);
    setTimeout(() => setGenerating(null), 2000);
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border-t-4 border-blue-500 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">📦 SCM REPORTS</h3>
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
                onClick={() => handleGenerate(`scm-${i}`)}
                disabled={generating === `scm-${i}`}
                className={`flex-shrink-0 px-3 py-1.5 text-[10px] font-medium rounded-md transition-all ${
                  generating === `scm-${i}`
                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 animate-neural-pulse'
                    : 'bg-blue-600 hover:bg-blue-500 text-white'
                }`}
              >
                {generating === `scm-${i}` ? 'Generating...' : 'Generate'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
