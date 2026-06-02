import type { Brain } from '../../types';
import { BrainIcon } from './Icons8Placeholder';

interface BrainCardProps {
  brain: Brain;
  isActive: boolean;
  onClick: () => void;
  compact?: boolean;
}

export function BrainCard({ brain, isActive, onClick, compact }: BrainCardProps) {
  const healthColor = brain.status === 'healthy' ? 'text-green-400' : brain.status === 'stressed' ? 'text-yellow-400' : 'text-red-400';

  if (compact) {
    return (
      <button
        onClick={onClick}
        className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-300 ${
          isActive
            ? 'bg-green-900/30 border border-green-500/30 shadow-lg shadow-green-500/10'
            : 'bg-slate-800/50 border border-transparent hover:bg-slate-700/50'
        }`}
      >
        <BrainIcon size={16} className={healthColor} />
        <span className={`text-xs font-medium truncate max-w-[80px] ${isActive ? 'text-green-300' : 'text-slate-300'}`}>
          {brain.name}
        </span>
        <span className={`w-2 h-2 rounded-full ${healthColor.replace('text', 'bg')}`} />
      </button>
    );
  }

  return (
    <button
      onClick={onClick}
      className={`
        relative flex-shrink-0 w-[200px] h-[60px] rounded-xl cursor-pointer
        transition-all duration-[400ms] cubic-bezier(0.34, 1.56, 0.64, 1)
        hover:[transform:rotateX(5deg)_translateY(-8px)]
        ${isActive
          ? 'border-l-[3px] border-green-400 shadow-[0_20px_40px_rgba(0,255,128,0.15)] translate-y-[-12px] bg-slate-800'
          : 'opacity-80 bg-slate-800/60 hover:opacity-100 border border-slate-700/50'
        }
      `}
      style={{ perspective: '800px' }}
    >
      <div className="flex items-center gap-2 px-3 h-full">
        <BrainIcon size={20} className={healthColor} />
        <div className="flex-1 min-w-0 text-left">
          <div className={`text-xs font-semibold truncate ${isActive ? 'text-green-300' : 'text-slate-200'}`}>
            {brain.name}
          </div>
          <div className="text-[10px] text-slate-400">
            ${(brain.revenue_mtd / 1000000).toFixed(1)}M MTD
          </div>
        </div>
        <span className={`w-2.5 h-2.5 rounded-full ${healthColor.replace('text', 'bg')}`} />
      </div>
    </button>
  );
}
