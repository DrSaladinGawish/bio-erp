export interface Brain {
  id: string;
  name: string;
  type: string;
  revenue_mtd: number;
  health_score: number;
  status: 'healthy' | 'stressed' | 'critical';
}

export interface Organ {
  id: string;
  brain_id: string;
  name: string;
  status: 'healthy' | 'stressed' | 'critical';
  load_percent: number;
  cell_count: number;
  revenue?: number;
  alert_count?: number;
  trend?: number[];
}

export interface Cell {
  id: string;
  brain_id: string;
  organ_id: string;
  organ_name: string;
  action: string;
  type: 'born' | 'flagged' | 'died' | 'mutated';
  timestamp: string;
}

export interface Prediction {
  id: string;
  label: string;
  confidence: number;
  description: string;
}

export interface Prescription {
  id: string;
  label: string;
  description: string;
  action: string;
}

export type ModuleType = 'body' | 'brain' | 'organs' | 'cells';

export interface ModuleTab {
  id: string;
  label: string;
  path: string;
}

export interface BrainState {
  activeBrainId: string | null;
  brains: Brain[];
  organs: Organ[];
  cells: Cell[];
  activeModule: ModuleType;
  activeTab: string;
  isLoading: boolean;
  isDarkMode: boolean;
  sidebarCollapsed: boolean;
}

export type BrainAction =
  | { type: 'SET_BRAINS'; payload: Brain[] }
  | { type: 'SET_ACTIVE_BRAIN'; payload: string }
  | { type: 'SET_ORGANS'; payload: Organ[] }
  | { type: 'SET_CELLS'; payload: Cell[] }
  | { type: 'SET_MODULE'; payload: ModuleType }
  | { type: 'SET_TAB'; payload: string }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'TOGGLE_DARK_MODE' }
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'SWITCH_BRAIN'; payload: string };
