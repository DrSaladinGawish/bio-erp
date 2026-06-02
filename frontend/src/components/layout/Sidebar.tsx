import { useBrain } from '../../hooks/useBrain';
import { BrainIcon, HeartIcon, DnaIcon, CellIcon } from '../common/Icons8Placeholder';
import type { ModuleType } from '../../types';

const modules: { id: ModuleType; label: string; Icon: typeof BrainIcon }[] = [
  { id: 'body', label: 'The Body', Icon: HeartIcon },
  { id: 'brain', label: 'Brain', Icon: BrainIcon },
  { id: 'organs', label: 'Organs', Icon: DnaIcon },
  { id: 'cells', label: 'Cells', Icon: CellIcon },
];

export function Sidebar() {
  const { state, dispatch } = useBrain();

  const isCollapsed = state.sidebarCollapsed;

  return (
    <aside
      className={`fixed left-0 top-[80px] bottom-0 z-40 transition-all duration-300 bg-[#0F172A] dark:bg-[#020617] border-r border-slate-700/50 ${
        isCollapsed ? 'w-[64px]' : 'w-[240px]'
      }`}
    >
      <nav className="flex flex-col h-full">
        <div className="flex-1 py-4 space-y-1 px-2">
          {modules.map(({ id, label, Icon }) => {
            const isActive = state.activeModule === id;
            return (
              <button
                key={id}
                onClick={() => dispatch({ type: 'SET_MODULE', payload: id })}
                title={isCollapsed ? label : undefined}
                className={`
                  w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-300 group relative
                  ${isActive
                    ? 'bg-[rgba(34,197,94,0.15)] border-l-[3px] border-green-400'
                    : 'border-l-[3px] border-transparent hover:bg-slate-800/50'
                  }
                `}
              >
                <Icon
                  size={20}
                  className={`flex-shrink-0 transition-all duration-300 ${
                    isActive ? 'text-green-400' : 'text-slate-400 group-hover:text-slate-200 group-hover:brightness-110'
                  }`}
                />
                {!isCollapsed && (
                  <span className={`text-sm font-medium transition-colors ${
                    isActive ? 'text-green-300' : 'text-slate-400 group-hover:text-slate-200'
                  }`}>
                    {label}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <div className="p-2 border-t border-slate-700/50">
          <button
            onClick={() => dispatch({ type: 'TOGGLE_SIDEBAR' })}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition-all"
            title={isCollapsed ? 'Expand' : 'Collapse'}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {isCollapsed
                ? <path d="M9 18l6-6-6-6" />
                : <path d="M15 18l-6-6 6-6" />
              }
            </svg>
            {!isCollapsed && <span className="text-xs">Collapse</span>}
          </button>
        </div>
      </nav>
    </aside>
  );
}
