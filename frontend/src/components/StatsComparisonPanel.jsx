import { StatRow } from "./StatBar";

const ROWS = [
  { key: "total_shots", label: "Finalizações" },
  { key: "shots_on_target", label: "Finalizações no alvo" },
  { key: "corners", label: "Escanteios" },
  { key: "yellow_cards", label: "Cartões Amarelos" },
  { key: "red_cards", label: "Cartões Vermelhos" },
  { key: "fouls", label: "Faltas" },
  { key: "offsides", label: "Impedimentos" },
];

export default function StatsComparisonPanel({ homeName, awayName, snapshot }) {
  const s = snapshot || {};
  const rows = ROWS.map((r) => ({
    ...r,
    home: s[`${r.key}_home`] ?? 0,
    away: s[`${r.key}_away`] ?? 0,
  }));

  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="flex items-center justify-between mb-4 text-sm font-medium">
        <span className="text-blue-400 truncate">{homeName}</span>
        <span className="text-red-400 truncate">{awayName}</span>
      </div>
      <div className="space-y-3.5">
        {rows.map((r) => (
          <StatRow key={r.key} label={r.label} home={r.home} away={r.away} statKey={r.key} />
        ))}
      </div>
    </div>
  );
}
