import { useMemo } from 'react';
import { useBrain } from './useBrain';

export function useCells() {
  const { state } = useBrain();
  return useMemo(() => ({
    cells: state.cells,
    isLoading: state.isLoading,
  }), [state.cells, state.isLoading]);
}
