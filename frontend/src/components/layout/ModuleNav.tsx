import { useMemo } from 'react';
import { useBrain } from '../../hooks/useBrain';
import type { ModuleTab } from '../../types';

const moduleTabs: Record<string, ModuleTab[]> = {
  body: [
    { id: 'dashboard', label: 'Dashboard', path: '/body/dashboard' },
    { id: 'brain-comparison', label: 'Brain Comparison', path: '/body/comparison' },
    { id: 'cross-brain-audit', label: 'Cross-Brain Audit', path: '/body/audit' },
    { id: 'cross-brain-reports', label: 'Cross-Brain Reports', path: '/body/reports' },
  ],
  brain: [
    { id: 'directory', label: 'Directory', path: '/brain/directory' },
    { id: 'add-company', label: 'Add Company', path: '/brain/add' },
    { id: 'brain-health', label: 'Brain Health', path: '/brain/health' },
    { id: 'cross-brain', label: 'Cross-Brain', path: '/brain/cross' },
  ],
  organs: [
    { id: 'organ-directory', label: 'Organ Directory', path: '/organs/directory' },
    { id: 'organ-performance', label: 'Organ Performance', path: '/organs/performance' },
    { id: 'organ-alerts', label: 'Organ Alerts', path: '/organs/alerts' },
    { id: 'organ-map', label: 'Organ Map', path: '/organs/map' },
  ],
  cells: [
    { id: 'cell-registry', label: 'Cell Registry', path: '/cells/registry' },
    { id: 'cell-activity', label: 'Cell Activity', path: '/cells/activity' },
    { id: 'cell-lifecycle', label: 'Cell Lifecycle', path: '/cells/lifecycle' },
    { id: 'cell-analytics', label: 'Cell Analytics', path: '/cells/analytics' },
  ],
};

export function ModuleNav() {
  const { state, dispatch } = useBrain();

  const tabs = useMemo(() => moduleTabs[state.activeModule] || moduleTabs.body, [state.activeModule]);

  return (
    <nav className="sticky top-[80px] z-30 h-[48px] bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 flex items-center gap-1 px-4 overflow-x-auto transition-all duration-300"
      style={{ scrollbarWidth: 'none' }}
    >
      {tabs.map(tab => {
        const isActive = state.activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => dispatch({ type: 'SET_TAB', payload: tab.id })}
            className={`
              relative px-4 py-2 text-[13px] font-medium rounded-full transition-all duration-200
              ${isActive
                ? 'text-blue-600 dark:text-blue-400'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
              }
            `}
          >
            {tab.label}
            {isActive && (
              <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-8 h-[2px] bg-blue-500 rounded-full transition-all duration-200" />
            )}
          </button>
        );
      })}
    </nav>
  );
}
