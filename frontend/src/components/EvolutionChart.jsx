import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

export default function EvolutionChart({ snapshots, homeName, awayName, metric = "corners" }) {
  if (!snapshots || snapshots.length === 0) {
    return (
      <div className="bg-panel border border-border rounded-xl p-4 sm:p-5 flex items-center justify-center h-72 text-muted text-sm">
        Ainda sem snapshots coletados para esta partida.
      </div>
    );
  }

  const sorted = [...snapshots].sort((a, b) => a.minute - b.minute);
  const last = sorted[sorted.length - 1];
  const homeKey = `${metric}_home`;
  const awayKey = `${metric}_away`;

  const rateHome = last[homeKey] / Math.max(last.minute, 1);
  const rateAway = last[awayKey] / Math.max(last.minute, 1);
  const projHome = +(rateHome * 90).toFixed(1);
  const projAway = +(rateAway * 90).toFixed(1);

  const chartData = sorted.map((s, i) => ({
    minute: s.minute,
    home: s[homeKey],
    away: s[awayKey],
    projHome: i === sorted.length - 1 ? s[homeKey] : null,
    projAway: i === sorted.length - 1 ? s[awayKey] : null,
  }));
  if (last.minute < 90) {
    chartData.push({ minute: 90, home: null, away: null, projHome, projAway });
  }

  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-slate-200">
          EVOLUÇÃO DA PARTIDA (SNAPSHOTS A CADA 5 MIN)
        </span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#232733" />
          <XAxis dataKey="minute" tickFormatter={(m) => `${m}'`} stroke="#8a90a2" fontSize={12} />
          <YAxis stroke="#8a90a2" fontSize={12} />
          <Tooltip
            contentStyle={{ background: "#171a24", border: "1px solid #232733", borderRadius: 8, fontSize: 12 }}
            labelFormatter={(m) => `Minuto ${m}'`}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="home" name={homeName} stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
          <Line type="monotone" dataKey="away" name={awayName} stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
          <Line
            type="monotone"
            dataKey="projHome"
            name={`Proj: ${projHome}`}
            stroke="#3b82f6"
            strokeDasharray="5 4"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="projAway"
            name={`Proj: ${projAway}`}
            stroke="#ef4444"
            strokeDasharray="5 4"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
