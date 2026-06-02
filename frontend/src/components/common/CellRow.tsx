import { useEffect, useState } from 'react';
import type { Cell } from '../../types';

interface CellRowProps {
  cell: Cell;
}

const typeConfig = {
  born: { dot: '🟢', bg: 'bg-green-500/10', border: 'border-green-500/20' },
  flagged: { dot: '🟡', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20' },
  died: { dot: '🔴', bg: 'bg-red-500/10', border: 'border-red-500/20' },
  mutated: { dot: '🔵', bg: 'bg-blue-500/10', border: 'border-blue-500/20' },
};

export function CellRow({ cell }: CellRowProps) {
  const [visible, setVisible] = useState(false);
  const cfg = typeConfig[cell.type];
  const time = new Date(cell.timestamp).toLocaleTimeString();

  useEffect(() => {
    const frame = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <div
      className={`
        flex items-center gap-3 px-3 py-2 text-xs border-l-2 rounded-r-lg
        transition-all duration-200
        ${cfg.bg} ${cfg.border}
        ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-[-8px]'}
      `}
    >
      <span className="text-sm">{cfg.dot}</span>
      <span className="text-slate-400 w-[72px] flex-shrink-0 font-mono">{time}</span>
      <span className="font-mono text-[10px] text-slate-500 w-[72px] flex-shrink-0">{cell.id}</span>
      <span className="text-slate-700 dark:text-slate-200 flex-1 truncate">{cell.action}</span>
      <span className="text-slate-400 flex-shrink-0">{cell.organ_name}</span>
    </div>
  );
}
