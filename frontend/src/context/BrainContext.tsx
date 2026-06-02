import React, { createContext, useReducer, useEffect, useCallback, type ReactNode } from 'react';
import type { BrainState, BrainAction, Brain, Organ, Cell } from '../types';

const initialState: BrainState = {
  activeBrainId: null,
  brains: [],
  organs: [],
  cells: [],
  activeModule: 'body',
  activeTab: 'dashboard',
  isLoading: false,
  isDarkMode: localStorage.getItem('bio-erp-dark-mode') === 'true',
  sidebarCollapsed: false,
};

const mockBrains: Brain[] = [
  { id: 'brain-a', name: 'Company A', type: 'Retail', revenue_mtd: 2000000, health_score: 94, status: 'healthy' },
  { id: 'brain-b', name: 'Company B', type: 'Events', revenue_mtd: 1000000, health_score: 88, status: 'healthy' },
  { id: 'brain-c', name: 'Company C', type: 'Manufacturing', revenue_mtd: 5000000, health_score: 72, status: 'stressed' },
];

const mockOrgans: Organ[] = [
  { id: 'organ-1', brain_id: 'brain-a', name: 'Procurement', status: 'healthy', load_percent: 65, cell_count: 1420, revenue: 800000, alert_count: 0, trend: [60, 62, 58, 63, 65, 64, 65] },
  { id: 'organ-2', brain_id: 'brain-a', name: 'Inventory', status: 'healthy', load_percent: 45, cell_count: 890, revenue: 450000, alert_count: 0, trend: [40, 42, 44, 43, 45, 44, 45] },
  { id: 'organ-3', brain_id: 'brain-a', name: 'Sales', status: 'stressed', load_percent: 88, cell_count: 2340, revenue: 1200000, alert_count: 2, trend: [80, 82, 85, 86, 88, 87, 88] },
  { id: 'organ-4', brain_id: 'brain-a', name: 'HR', status: 'healthy', load_percent: 30, cell_count: 340, revenue: 120000, alert_count: 0, trend: [28, 29, 30, 30, 31, 30, 30] },
];

const mockCells: Cell[] = [
  { id: 'cell-001', brain_id: 'brain-a', organ_id: 'organ-1', organ_name: 'Procurement', action: 'PO-2024-0421 created', type: 'born', timestamp: new Date().toISOString() },
  { id: 'cell-002', brain_id: 'brain-a', organ_id: 'organ-3', organ_name: 'Sales', action: 'SO-2024-0891 flagged', type: 'flagged', timestamp: new Date(Date.now() - 5000).toISOString() },
  { id: 'cell-003', brain_id: 'brain-a', organ_id: 'organ-2', organ_name: 'Inventory', action: 'INV-2024-0312 adjusted', type: 'mutated', timestamp: new Date(Date.now() - 15000).toISOString() },
  { id: 'cell-004', brain_id: 'brain-a', organ_id: 'organ-3', organ_name: 'Sales', action: 'Invoice INV-2024-0567 paid', type: 'born', timestamp: new Date(Date.now() - 25000).toISOString() },
  { id: 'cell-005', brain_id: 'brain-a', organ_id: 'organ-1', organ_name: 'Procurement', action: 'PO-2024-0419 closed', type: 'died', timestamp: new Date(Date.now() - 35000).toISOString() },
  { id: 'cell-006', brain_id: 'brain-b', organ_id: 'organ-1', organ_name: 'Procurement', action: 'RFQ-2024-0102 sent', type: 'born', timestamp: new Date(Date.now() - 10000).toISOString() },
];

function brainReducer(state: BrainState, action: BrainAction): BrainState {
  switch (action.type) {
    case 'SET_BRAINS':
      return { ...state, brains: action.payload };
    case 'SET_ACTIVE_BRAIN':
      return { ...state, activeBrainId: action.payload };
    case 'SET_ORGANS':
      return { ...state, organs: action.payload };
    case 'SET_CELLS':
      return { ...state, cells: action.payload };
    case 'SET_MODULE':
      return { ...state, activeModule: action.payload, activeTab: getDefaultTab(action.payload) };
    case 'SET_TAB':
      return { ...state, activeTab: action.payload };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'TOGGLE_DARK_MODE': {
      const next = !state.isDarkMode;
      localStorage.setItem('bio-erp-dark-mode', String(next));
      return { ...state, isDarkMode: next };
    }
    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarCollapsed: !state.sidebarCollapsed };
    case 'SWITCH_BRAIN':
      return {
        ...state,
        activeBrainId: action.payload,
        isLoading: false,
        organs: action.payload === state.activeBrainId ? state.organs : [],
        cells: action.payload === state.activeBrainId ? state.cells : [],
      };
    default:
      return state;
  }
}

function getDefaultTab(module: string): string {
  switch (module) {
    case 'body': return 'dashboard';
    case 'brain': return 'directory';
    case 'organs': return 'organ-directory';
    case 'cells': return 'cell-registry';
    default: return 'dashboard';
  }
}

export interface BrainContextValue {
  state: BrainState;
  dispatch: React.Dispatch<BrainAction>;
  switchBrain: (id: string) => Promise<void>;
  fetchOrgans: (brainId: string) => Promise<void>;
  fetchCells: (brainId: string) => Promise<void>;
  fetchBrains: () => Promise<void>;
}

export const BrainContext = createContext<BrainContextValue | null>(null);

export function BrainProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(brainReducer, initialState);

  const fetchBrains = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/brains');
      if (res.ok) {
        const data = await res.json();
        dispatch({ type: 'SET_BRAINS', payload: data });
        return;
      }
    } catch { /* fallback to mock */ }
    dispatch({ type: 'SET_BRAINS', payload: mockBrains });
    if (!state.activeBrainId && mockBrains.length > 0) {
      dispatch({ type: 'SET_ACTIVE_BRAIN', payload: mockBrains[0].id });
    }
  }, [state.activeBrainId]);

  const fetchOrgans = useCallback(async (brainId: string) => {
    try {
      const res = await fetch(`/api/v1/brains/${brainId}/organs`);
      if (res.ok) {
        const data = await res.json();
        dispatch({ type: 'SET_ORGANS', payload: data });
        return;
      }
    } catch { /* fallback */ }
    dispatch({ type: 'SET_ORGANS', payload: mockOrgans.filter(o => o.brain_id === brainId) });
  }, []);

  const fetchCells = useCallback(async (brainId: string) => {
    try {
      const res = await fetch(`/api/v1/brains/${brainId}/cells`);
      if (res.ok) {
        const data = await res.json();
        dispatch({ type: 'SET_CELLS', payload: data });
        return;
      }
    } catch { /* fallback */ }
    dispatch({ type: 'SET_CELLS', payload: mockCells.filter(c => c.brain_id === brainId) });
  }, []);

  const switchBrain = useCallback(async (id: string) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    await new Promise(r => setTimeout(r, 200));
    dispatch({ type: 'SWITCH_BRAIN', payload: id });
    await Promise.all([fetchOrgans(id), fetchCells(id)]);
  }, [fetchOrgans, fetchCells]);

  useEffect(() => {
    fetchBrains();
  }, [fetchBrains]);

  useEffect(() => {
    if (state.activeBrainId) {
      fetchOrgans(state.activeBrainId);
      fetchCells(state.activeBrainId);
    }
  }, [state.activeBrainId, fetchOrgans, fetchCells]);

  useEffect(() => {
    if (state.isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [state.isDarkMode]);

  return (
    <BrainContext.Provider value={{ state, dispatch, switchBrain, fetchOrgans, fetchCells, fetchBrains }}>
      {children}
    </BrainContext.Provider>
  );
}
