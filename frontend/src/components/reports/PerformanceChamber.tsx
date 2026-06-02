import { useState } from 'react';

const reports = [
  { icon: '⚡', title: 'Organ Load Analysis', desc: 'Real-time load distribution across all organs with bottleneck identification' },
  { icon: '🔄', title: 'Cell Throughput Velocity', desc: 'Transaction processing speed analysis with latency breakdown by organ type' },
  { icon: '🧠', title: 'Brain Health Trend', desc: 'Historical health score tracking for all brains with anomaly detection' },
  { icon: '🔮', title: 'Predictive Diagnostics', desc: 'ML-based prediction of potential organ failures and cell mutation hotspots' },
  { icon: '🔗', title: 'Cross-Organ Efficiency', desc: 'Inter-organ communication efficiency metrics with optimization recommendations' },
];

export function PerformanceChamber() {
  const [generating, setGenerating] = useState<string | null>(null);

  const handleGenerate = (id: string) => {
    setGenerating(id);
    setTimeout(() => setGenerating(null), 2000);
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border-t-4 border-purple-500 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">🎯 PERFORMANCE REPORTS</h3>
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
                onClick={() => handleGenerate(`perf-${i}`)}
                disabled={generating === `perf-${i}`}
                className={`flex-shrink-0 px-3 py-1.5 text-[10px] font-medium rounded-md transition-all ${
                  generating === `perf-${i}`
                    ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 animate-neural-pulse'
                    : 'bg-purple-600 hover:bg-purple-500 text-white'
                }`}
              >
                {generating === `perf-${i}` ? 'Generating...' : 'Generate'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
