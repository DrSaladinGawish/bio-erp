import { useEffect, useState } from 'react';
import { useBrain } from '../../hooks/useBrain';
import { BrainCard } from '../common/BrainCard';
import { PulseIcon } from '../common/Icons8Placeholder';

function AnimatedNumber({ value, duration = 1500 }: { value: number; duration?: number }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let start = 0;
    const step = Math.ceil(value / (duration / 16));
    const timer = setInterval(() => {
      start += step;
      if (start >= value) { setDisplay(value); clearInterval(timer); }
      else setDisplay(start);
    }, 16);
    return () => clearInterval(timer);
  }, [value, duration]);
  return <span>${(display / 1000000).toFixed(1)}M</span>;
}

export function VitalsBanner() {
  const { state, switchBrain } = useBrain();
  const totalRevenue = state.brains.reduce((sum, b) => sum + b.revenue_mtd, 0);
  const totalCells = state.brains.length * 1000;
  const avgHealth = state.brains.length
    ? Math.round(state.brains.reduce((s, b) => s + b.health_score, 0) / state.brains.length)
    : 0;

  const healthAngle = (avgHealth / 100) * 270;
  const healthColor = avgHealth > 80 ? '#22C55E' : avgHealth > 60 ? '#EAB308' : '#EF4444';

  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-[#0B1120] to-[#0F172A] rounded-2xl p-6 mb-6 border border-slate-700/50">
      {/* Animated EKG line */}
      <div className="absolute top-0 left-0 right-0 h-[2px] overflow-hidden opacity-30">
        <div className="h-full w-full bg-green-400 animate-heartbeat" style={{ transformOrigin: 'left center' }} />
      </div>

      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <PulseIcon size={20} className="text-green-400" />
            The Vitals
          </h2>
          <p className="text-xs text-slate-400 mt-1">System-wide health overview</p>
        </div>
        <div className="flex items-center gap-2">
          {state.brains.map(b => (
            <BrainCard
              key={b.id}
              brain={b}
              isActive={state.activeBrainId === b.id}
              onClick={() => switchBrain(b.id)}
              compact
            />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-6">
        {/* Total Revenue */}
        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
          <div className="text-xs text-slate-400 mb-1">Total Revenue MTD</div>
          <div className="text-2xl font-bold text-green-400">
            <AnimatedNumber value={totalRevenue} />
          </div>
        </div>

        {/* Active Cells */}
        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
          <div className="text-xs text-slate-400 mb-1">Active Cells</div>
          <div className="text-2xl font-bold text-blue-400">{totalCells.toLocaleString()}</div>
        </div>

        {/* System Pulse */}
        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
          <div className="text-xs text-slate-400 mb-3">System Pulse</div>
          <div className="flex items-center gap-2 h-8">
            <svg className="w-full h-8" viewBox="0 0 120 24" preserveAspectRatio="none">
              <polyline
                points="0,12 10,12 15,4 20,20 25,12 35,12 40,8 45,16 50,12 60,12 65,6 70,18 75,12 85,12 90,10 95,14 100,12 110,12 115,5 120,19"
                fill="none"
                stroke="#22C55E"
                strokeWidth="1.5"
                className="animate-heartbeat"
              />
            </svg>
          </div>
        </div>

        {/* Body Temperature Gauge */}
        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
          <div className="text-xs text-slate-400 mb-1">Body Health</div>
          <div className="flex items-center gap-3">
            <svg width="48" height="48" viewBox="0 0 48 48">
              <circle cx="24" cy="24" r="20" fill="none" stroke="#1E293B" strokeWidth="4" />
              <circle
                cx="24" cy="24" r="20"
                fill="none"
                stroke={healthColor}
                strokeWidth="4"
                strokeDasharray={`${(healthAngle / 360) * 126} 126`}
                transform="rotate(-135 24 24)"
                strokeLinecap="round"
              />
              <text x="24" y="26" textAnchor="middle" fill="white" fontSize="10" fontWeight="bold">
                {avgHealth}°
              </text>
            </svg>
            <div className="text-xs text-slate-400">
              <span className="text-green-400 font-bold">{avgHealth}%</span> healthy
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
