import type { Organ } from '../../types';
import { OrganIcon } from './Icons8Placeholder';

interface OrganCardProps {
  organ: Organ;
  onClick?: () => void;
}

export function OrganCard({ organ, onClick }: OrganCardProps) {
  const statusBg = organ.status === 'healthy' ? 'bg-green-400' : organ.status === 'stressed' ? 'bg-yellow-400' : 'bg-red-400';

  return (
    <button
      onClick={onClick}
      className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm hover:shadow-lg hover:-translate-y-1 transition-all duration-300 text-left w-full border border-slate-200 dark:border-slate-700"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <OrganIcon size={20} className="text-slate-600 dark:text-slate-300" />
          <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-100">{organ.name}</h3>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${statusBg}`} />
          {organ.alert_count && organ.alert_count > 0 && (
            <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
              {organ.alert_count}
            </span>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <div>
          <div className="flex justify-between text-[11px] text-slate-500 dark:text-slate-400 mb-1">
            <span>Load</span>
            <span>{organ.load_percent}%</span>
          </div>
          <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                organ.load_percent > 80 ? 'bg-red-400' : organ.load_percent > 60 ? 'bg-yellow-400' : 'bg-green-400'
              }`}
              style={{ width: `${organ.load_percent}%` }}
            />
          </div>
        </div>

        <div className="flex justify-between text-[11px]">
          <span className="text-slate-500 dark:text-slate-400">{organ.cell_count.toLocaleString()} cells</span>
          {organ.revenue !== undefined && (
            <span className="text-green-600 dark:text-green-400 font-medium">
              ${(organ.revenue / 1000000).toFixed(1)}M
            </span>
          )}
        </div>

        {organ.trend && (
          <svg className="w-full h-6" viewBox="0 0 100 20" preserveAspectRatio="none">
            <path
              d={`M ${organ.trend.map((v, i) => `${(i / (organ.trend!.length - 1)) * 100},${20 - (v / 100) * 18}`).join(' L ')}`}
              fill="none"
              stroke={organ.load_percent > 80 ? '#ef4444' : organ.load_percent > 60 ? '#eab308' : '#22c55e'}
              strokeWidth="1.5"
            />
          </svg>
        )}
      </div>
    </button>
  );
}
