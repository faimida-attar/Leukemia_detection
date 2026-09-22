import React from 'react';
import { HelpCircle, TrendingUp, Sparkles } from 'lucide-react';

export default function MetricCard({ title, value, unit, description, benchmark, quality, color = 'sky' }) {
  const colorMap = {
    sky: 'border-sky-200 bg-sky-50/50 text-sky-900 header-sky',
    emerald: 'border-emerald-200 bg-emerald-50/50 text-emerald-900',
    indigo: 'border-indigo-200 bg-indigo-50/50 text-indigo-900',
    amber: 'border-amber-200 bg-amber-50/50 text-amber-900',
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs hover:shadow-md transition-shadow relative overflow-hidden flex flex-col justify-between">
      {/* Top Header */}
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">{title}</span>
          {quality && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-sky-100 text-sky-800 border border-sky-200">
              {quality}
            </span>
          )}
        </div>

        {/* Main Value Display */}
        <div className="flex items-baseline gap-1.5 my-2">
          <span className="text-3xl font-extrabold text-slate-900 tracking-tight">{value}</span>
          {unit && <span className="text-sm font-semibold text-slate-500">{unit}</span>}
        </div>
      </div>

      {/* Description & Benchmark */}
      <div className="pt-3 border-t border-slate-100 mt-3 space-y-1">
        <p className="text-xs text-slate-500 leading-snug">{description}</p>
        {benchmark && (
          <div className="text-[11px] font-medium text-sky-700 flex items-center gap-1 pt-1">
            <TrendingUp className="w-3 h-3 text-sky-600" />
            <span>Benchmark: {benchmark}</span>
          </div>
        )}
      </div>
    </div>
  );
}
