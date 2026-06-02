import { BrainIcon } from '../common/Icons8Placeholder';
import type { Prediction, Prescription } from '../../types';

const mockPredictions: Prediction[] = [
  { id: 'pred-1', label: 'Revenue Growth', confidence: 87, description: 'Q2 revenue projected +12% based on current organ throughput' },
  { id: 'pred-2', label: 'Organ Strain', confidence: 62, description: 'Sales organ approaching critical load within 14 days' },
  { id: 'pred-3', label: 'Cell Mutation Rate', confidence: 73, description: 'Transaction error rate may increase 3% without intervention' },
];

const mockPrescriptions: Prescription[] = [
  { id: 'rx-1', label: 'Scale Sales Organ', description: 'Allocate 2 additional units to Sales to reduce load from 88% to 65%', action: 'scale_sales' },
  { id: 'rx-2', label: 'Audit Cell Mutations', description: 'Run diagnostic on mutated cells in Inventory to identify root cause', action: 'audit_cells' },
  { id: 'rx-3', label: 'Optimize Procurement', description: 'Enable auto-reorder rules for top 10 SKUs to improve throughput', action: 'optimize_procurement' },
];

export function PrognosisPanel() {
  return (
    <section className="mb-6">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">The Prognosis</h3>
      <div className="grid grid-cols-2 gap-6">
        {/* Neural Prediction */}
        <div className="bg-slate-800/80 rounded-xl p-5 border border-blue-500/20">
          <div className="flex items-center gap-2 mb-4">
            <BrainIcon size={20} className="text-blue-400" />
            <h4 className="text-sm font-semibold text-blue-300">Neural Prediction</h4>
          </div>
          <div className="space-y-4">
            {mockPredictions.map(pred => (
              <div key={pred.id}>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-medium text-slate-200">{pred.label}</span>
                  <span className="text-[10px] text-blue-400 font-mono">{pred.confidence}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden mb-1">
                  <div
                    className="h-full rounded-full bg-blue-500 transition-all duration-500"
                    style={{ width: `${pred.confidence}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-400 leading-relaxed">{pred.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Prescription */}
        <div className="bg-slate-800/80 rounded-xl p-5 border border-green-500/20">
          <div className="flex items-center gap-2 mb-4">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#22C55E" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M9 12l2 2 4-4" />
            </svg>
            <h4 className="text-sm font-semibold text-green-300">Prescription</h4>
          </div>
          <div className="space-y-3">
            {mockPrescriptions.map(rx => (
              <div key={rx.id} className="bg-slate-700/50 rounded-lg p-3 border border-slate-600/30">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h5 className="text-xs font-semibold text-slate-200">{rx.label}</h5>
                    <p className="text-[10px] text-slate-400 mt-0.5">{rx.description}</p>
                  </div>
                  <button className="flex-shrink-0 px-2.5 py-1 text-[10px] font-medium bg-green-600 hover:bg-green-500 text-white rounded-md transition-colors">
                    Execute
                  </button>
                </div>
              </div>
            ))}
          </div>
          <button className="w-full mt-3 py-2 text-xs font-semibold bg-green-600 hover:bg-green-500 text-white rounded-lg transition-colors">
            Execute All
          </button>
        </div>
      </div>
    </section>
  );
}
