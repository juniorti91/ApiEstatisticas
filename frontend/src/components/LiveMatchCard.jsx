import { useState } from "react";
import { Star } from "lucide-react";

const TABS = ["Visão Geral", "Estatísticas", "Odds", "Eventos", "Comparativo", "Histórico"];

function TeamBadge({ name, color }) {
  const initial = name?.[0]?.toUpperCase() || "?";
  return (
    <div
      className="w-11 h-11 rounded-full flex items-center justify-center font-bold text-sm border-2"
      style={{ borderColor: color, color }}
    >
      {initial}
    </div>
  );
}

export default function LiveMatchCard({ match, activeTab, onTabChange, hideTabs = false }) {
  if (!match) return null;
  const possessionHome = match.possessionHome ?? 50;
  const possessionAway = 100 - possessionHome;

  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="flex items-center gap-1.5 bg-red-500/15 text-red-400 text-xs font-semibold px-2.5 py-1 rounded-md shrink-0">
            <span className="relative flex w-2 h-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
              <span className="relative inline-flex w-2 h-2 rounded-full bg-red-500" />
            </span>
            AO VIVO
          </span>
          <span className="text-sm text-slate-300 font-medium whitespace-nowrap">
            {match.elapsed_minutes}' {match.periodLabel}
          </span>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <div className="text-right">
            <div className="text-sm text-slate-300">{match.league?.name}</div>
            <div className="text-xs text-muted">{match.round}</div>
          </div>
          <Star size={16} className="text-muted shrink-0" />
        </div>
      </div>

      <div className="flex items-center justify-center gap-3 sm:gap-10 py-3">
        <div className="flex flex-col items-center gap-2 w-16 sm:w-32 min-w-0">
          <TeamBadge name={match.home_team?.name} color="#3b82f6" />
          <span className="text-xs sm:text-sm text-slate-200 text-center truncate w-full">{match.home_team?.name}</span>
        </div>
        <div className="text-center shrink-0">
          <div className="text-2xl sm:text-4xl font-bold text-slate-50 tracking-wide">
            {match.goals_home} - {match.goals_away}
          </div>
          <div className="text-[11px] text-muted mt-2">Posse de Bola</div>
          <div className="flex items-center gap-1.5 sm:gap-2 mt-1 w-32 sm:w-48">
            <span className="text-xs text-blue-400 w-7 sm:w-8">{possessionHome}%</span>
            <div className="flex-1 h-1.5 rounded-full bg-panel2 overflow-hidden flex">
              <div className="h-full bg-blue-500" style={{ width: `${possessionHome}%` }} />
              <div className="h-full bg-red-500" style={{ width: `${possessionAway}%` }} />
            </div>
            <span className="text-xs text-red-400 w-7 sm:w-8 text-right">{possessionAway}%</span>
          </div>
        </div>
        <div className="flex flex-col items-center gap-2 w-16 sm:w-32 min-w-0">
          <TeamBadge name={match.away_team?.name} color="#ef4444" />
          <span className="text-xs sm:text-sm text-slate-200 text-center truncate w-full">{match.away_team?.name}</span>
        </div>
      </div>

      {!hideTabs && (
      <div className="flex items-center gap-4 sm:gap-6 border-t border-border mt-3 pt-3 text-sm overflow-x-auto whitespace-nowrap">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            className={`pb-2 -mb-3 border-b-2 transition-colors shrink-0 ${
              activeTab === tab
                ? "border-accent text-accent font-medium"
                : "border-transparent text-muted hover:text-slate-200"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>
      )}
    </div>
  );
}
