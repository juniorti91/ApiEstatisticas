const ROWS = [
  { key: "total_shots", label: "Finalizações" },
  { key: "shots_on_target", label: "Finalizações no alvo" },
  { key: "corners", label: "Escanteios" },
  { key: "yellow_cards", label: "Cartões Amarelos" },
  { key: "red_cards", label: "Cartões Vermelhos" },
  { key: "fouls", label: "Faltas" },
  { key: "offsides", label: "Impedimentos" },
];

function Bar({ value, max, color, align }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className={`flex-1 h-2 rounded-full bg-panel2 overflow-hidden flex ${align === "right" ? "justify-end" : ""}`}>
      <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
    </div>
  );
}

export default function StatsComparisonPanel({ homeName, awayName, snapshot }) {
  const s = snapshot || {};
  const rows = ROWS.map((r) => ({
    ...r,
    home: s[`${r.key}_home`] ?? 0,
    away: s[`${r.key}_away`] ?? 0,
  }));
  const maxByRow = rows.map((r) => Math.max(r.home, r.away, 1));

  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="flex items-center justify-between mb-4 text-sm font-medium">
        <span className="text-blue-400 truncate">{homeName}</span>
        <span className="text-red-400 truncate">{awayName}</span>
      </div>
      <div className="space-y-3.5">
        {rows.map((r, i) => (
          <div key={r.key} className="flex items-center gap-1.5 sm:gap-3">
            <span className="w-6 sm:w-8 text-right text-sm text-slate-200 shrink-0">{r.home}</span>
            <Bar value={r.home} max={maxByRow[i]} color="#3b82f6" align="right" />
            <span className="w-16 sm:w-40 text-center text-[10px] sm:text-xs text-muted shrink-0 truncate">
              {r.label}
            </span>
            <Bar value={r.away} max={maxByRow[i]} color="#ef4444" />
            <span className="w-6 sm:w-8 text-sm text-slate-200 shrink-0">{r.away}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
