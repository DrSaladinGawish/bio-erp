import { useContext } from 'react';
import { BrainContext } from '../context/BrainContext';

export function useBrain() {
  const ctx = useContext(BrainContext);
  if (!ctx) throw new Error('useBrain must be used within BrainProvider');
  return ctx;
}
