import { useMemo } from 'react';
import { useBrain } from './useBrain';

export function useOrgans() {
  const { state } = useBrain();
  return useMemo(() => ({
    organs: state.organs,
    isLoading: state.isLoading,
  }), [state.organs, state.isLoading]);
}
