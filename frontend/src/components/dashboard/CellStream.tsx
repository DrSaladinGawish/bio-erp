import { useRef, useEffect } from 'react';
import { useCells } from '../../hooks/useCells';
import { CellRow } from '../common/CellRow';

export function CellStream() {
  const { cells, isLoading } = useCells();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
  }, [cells]);

  const recentCells = cells.slice(0, 20);

  return (
    <section className="mb-6">
      <div className="bg-slate-800/80 rounded-xl border border-slate-700/50 overflow-hidden">
        <div className="px-4 py-2.5 border-b border-slate-700/50 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            LIVE CELL ACTIVITY
            <span className="text-[10px] text-slate-500 font-normal">(Last 60 seconds)</span>
          </h3>
          <span className="text-xs text-slate-400">{recentCells.length} events</span>
        </div>
        <div
          ref={containerRef}
          className="overflow-y-auto"
          style={{ maxHeight: '400px' }}
        >
          {isLoading ? (
            <div className="p-4 text-center text-xs text-slate-500">Loading cell activity...</div>
          ) : recentCells.length === 0 ? (
            <div className="p-4 text-center text-xs text-slate-500">No recent cell activity</div>
          ) : (
            <div className="space-y-1 p-2">
              {recentCells.map(cell => (
                <CellRow key={cell.id} cell={cell} />
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
