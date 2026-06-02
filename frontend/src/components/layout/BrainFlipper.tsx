import { useState, useRef } from 'react';
import { useBrain } from '../../hooks/useBrain';
import { BrainCard } from '../common/BrainCard';

export function BrainFlipper() {
  const { state, switchBrain } = useBrain();
  const [scrollPos, setScrollPos] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const scroll = (dir: 'left' | 'right') => {
    const container = containerRef.current;
    if (!container) return;
    const amount = 220;
    const newPos = dir === 'left'
      ? Math.max(0, scrollPos - amount)
      : Math.min(container.scrollWidth - container.clientWidth, scrollPos + amount);
    container.scrollTo({ left: newPos, behavior: 'smooth' });
    setScrollPos(newPos);
  };

  return (
    <div className="flex items-center gap-2 h-[80px] px-4 bg-slate-900/95 border-b border-slate-700/50 fixed top-0 left-0 right-0 z-50">
      <button
        onClick={() => scroll('left')}
        className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
      >
        ◀
      </button>

      <div
        ref={containerRef}
        className="flex-1 flex items-center gap-3 overflow-x-auto scrollbar-hide"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        {state.brains.map(brain => (
          <BrainCard
            key={brain.id}
            brain={brain}
            isActive={state.activeBrainId === brain.id}
            onClick={() => switchBrain(brain.id)}
          />
        ))}
      </div>

      <button
        onClick={() => scroll('right')}
        className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
      >
        ▶
      </button>

      {state.activeBrainId && (
        <div className="flex-shrink-0 text-xs text-green-400 font-medium ml-2 px-3 py-1 bg-green-900/30 rounded-full">
          Active: {state.brains.find(b => b.id === state.activeBrainId)?.name}
        </div>
      )}
    </div>
  );
}
