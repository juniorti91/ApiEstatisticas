import { useState } from "react";
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

// Pedido do usuario: o grafico so dizia "EVOLUÇÃO DA PARTIDA" sem deixar
// claro QUAL estatistica estava sendo plotada (estava fixo em escanteios,
// escondido atras de um prop `metric` que nenhuma tela realmente passava) -
// dai a pergunta "essa evolução é de que?". Agora isso fica explicito no
// titulo/legenda, e o usuario pode alternar entre metricas pra ver mais de
// uma evolucao, atendendo o "detalhar um pouco mais" tambem.
const METRICS = [
  { key: "corners", label: "Escanteios", shortLabel: "Escanteios", decimals: 0 },
  { key: "total_shots", label: "Finalizações", shortLabel: "Finalizações", decimals: 0 },
  { key: "shots_on_target", label: "Finalizações no Alvo", shortLabel: "No Alvo", decimals: 0 },
  { key: "dangerous_attacks", label: "Ataques Perigosos", shortLabel: "Ataques Perig.", decimals: 0 },
  { key: "xg", label: "Gols Esperados (xG)", shortLabel: "xG", decimals: 2 },
];

export default function EvolutionChart({ snapshots, homeName, awayName, metric = "corners" }) {
  const [selectedMetric, setSelectedMetric] = useState(metric);

  if (!snapshots || snapshots.length === 0) {
    return (
      <div className="bg-panel border border-border rounded-xl p-4 sm:p-5 flex items-center justify-center h-72 text-muted text-sm">
        Ainda sem snapshots coletados para esta partida.
      </div>
    );
  }

  const activeMetric = METRICS.find((m) => m.key === selectedMetric) || METRICS[0];
  const formatValue = (v) =>
    v === null || v === undefined ? v : Number(v).toFixed(activeMetric.decimals);

  const sorted = [...snapshots].sort((a, b) => a.minute - b.minute);
  const last = sorted[sorted.length - 1];
  const homeKey = `${activeMetric.key}_home`;
  const awayKey = `${activeMetric.key}_away`;

  const rateHome = last[homeKey] / Math.max(last.minute, 1);
  const rateAway = last[awayKey] / Math.max(last.minute, 1);
  const projHome = +(rateHome * 90).toFixed(activeMetric.decimals);
  const projAway = +(rateAway * 90).toFixed(activeMetric.decimals);

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
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <span className="text-sm font-medium text-slate-200">
          EVOLUÇÃO DA PARTIDA (SNAPSHOTS A CADA 5 MIN)
        </span>
        {/* Seletor de metrica: cada botao troca o que as duas linhas do
            grafico representam, projetando (linha tracejada) o valor final
            estimado ate os 90min com base no ritmo medio ate agora. */}
        <div className="flex items-center gap-1 bg-base/60 border border-border rounded-lg p-0.5">
          {METRICS.map((m) => (
            <button
              key={m.key}
              type="button"
              onClick={() => setSelectedMetric(m.key)}
              className={`text-xs px-2 py-1 rounded-md transition-colors ${
                m.key === activeMetric.key
                  ? "bg-accentdim text-accent font-semibold"
                  : "text-muted hover:text-slate-300"
              }`}
            >
              {m.shortLabel}
            </button>
          ))}
        </div>
      </div>
      <div className="text-xs text-muted mb-2">
        Acompanhando: <span className="text-slate-300 font-medium">{activeMetric.label}</span> acumulado(a) por
        minuto, com projeção (linha tracejada) para os 90min no ritmo atual.
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#232733" />
          <XAxis dataKey="minute" tickFormatter={(m) => `${m}'`} stroke="#8a90a2" fontSize={12} />
          <YAxis stroke="#8a90a2" fontSize={12} />
          <Tooltip
            contentStyle={{ background: "#171a24", border: "1px solid #232733", borderRadius: 8, fontSize: 12 }}
            labelFormatter={(m) => `Minuto ${m}'`}
            formatter={(value, name) => [formatValue(value), name]}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="home" name={homeName} stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
          <Line type="monotone" dataKey="away" name={awayName} stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
          <Line
            type="monotone"
            dataKey="projHome"
            name={`Proj: ${formatValue(projHome)}`}
            stroke="#3b82f6"
            strokeDasharray="5 4"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="projAway"
            name={`Proj: ${formatValue(projAway)}`}
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
