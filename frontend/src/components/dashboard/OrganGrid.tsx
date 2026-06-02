import { useOrgans } from '../../hooks/useOrgans';
import { OrganCard } from '../common/OrganCard';

export function OrganGrid() {
  const { organs, isLoading } = useOrgans();

  if (isLoading) {
    return (
      <section className="mb-6">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">The Organs</h3>
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-slate-800/50 rounded-xl h-[140px] animate-pulse border border-slate-700/30" />
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="mb-6">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">
        The Organs
        <span className="text-xs text-slate-500 font-normal ml-2">({organs.length} active)</span>
      </h3>
      <div className="grid grid-cols-4 gap-4">
        {organs.map(organ => (
          <OrganCard key={organ.id} organ={organ} />
        ))}
      </div>
    </section>
  );
}
