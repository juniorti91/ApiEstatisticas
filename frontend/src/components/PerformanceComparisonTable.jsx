import { useState } from "react";
import { ArrowUp, ArrowDown, Minus } from "lucide-react";
import Modal from "./Modal";

function TrendIcon({ trend }) {
  if (trend === "up") return <ArrowUp size={13} className="text-accent" />;
  if (trend === "down") return <ArrowDown size={13} className="text-red-400" />;
  return <Minus size={13} className="text-muted" />;
}

function trendLabel(trend) {
  if (trend === "up") return "subindo";
  if (trend === "down") return "caindo";
  return "estável";
}

function MetricsTable({ comparison, elapsedMinutes, dense = true }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm min-w-[420px]">
        <thead>
          <tr className="text-muted text-xs">
            <th className="text-left font-normal pb-2"></th>
            <th className="text-right font-normal pb-2">Média dos últimos {comparison.sample_size} jogos</th>
            <th className="text-right font-normal pb-2">No jogo atual (até {elapsedMinutes}')</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {comparison.metrics.map((m) => (
            <tr key={m.label}>
              <td className={`${dense ? "py-2" : "py-2.5"} text-slate-300`}>{m.label}</td>
              <td className={`${dense ? "py-2" : "py-2.5"} text-right text-slate-200`}>
                {m.home_avg_last.toFixed(1)} <span className="text-muted">/</span> {m.away_avg_last.toFixed(1)}
              </td>
              <td className={`${dense ? "py-2" : "py-2.5"} text-right`}>
                <span className="inline-flex items-center gap-1 text-slate-100">
                  {m.home_current}
                  <TrendIcon trend={m.home_trend} />
                </span>
                <span className="text-muted mx-1">/</span>
                <span className="inline-flex items-center gap-1 text-slate-100">
                  {m.away_current}
                  <TrendIcon trend={m.away_trend} />
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PerformanceComparisonTable({ comparison, elapsedMinutes, homeName, awayName }) {
  const [showModal, setShowModal] = useState(false);

  if (!comparison) return null;

  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="text-sm font-medium text-slate-200 mb-3">COMPARATIVO DE DESEMPENHO</div>
      <MetricsTable comparison={comparison} elapsedMinutes={elapsedMinutes} />
      <button
        onClick={() => setShowModal(true)}
        className="w-full mt-4 bg-accentdim text-accent text-sm font-medium py-2 rounded-lg hover:brightness-110"
      >
        VER ANÁLISE COMPLETA
      </button>

      <Modal
        open={showModal}
        onClose={() => setShowModal(false)}
        title={`Análise completa${homeName && awayName ? ` — ${homeName} x ${awayName}` : ""}`}
        widthClass="max-w-3xl"
      >
        <p className="text-xs text-muted mb-4">
          Comparação entre a média das últimas {comparison.sample_size} partidas de cada time e o
          desempenho registrado até o minuto {elapsedMinutes} da partida atual. As setas indicam se o
          ritmo do time na partida ao vivo está acima, abaixo ou em linha com a sua média recente.
        </p>

        <MetricsTable comparison={comparison} elapsedMinutes={elapsedMinutes} dense={false} />

        <div className="border-t border-border mt-5 pt-4">
          <div className="text-xs font-medium text-muted mb-2">LEITURA DAS TENDÊNCIAS</div>
          <ul className="space-y-1.5 text-xs text-slate-300">
            {comparison.metrics.map((m) => (
              <li key={m.label} className="flex items-center gap-1.5 flex-wrap">
                <span className="text-slate-200 font-medium">{m.label}:</span>
                <span>
                  {homeName || "Mandante"} {trendLabel(m.home_trend)}
                </span>
                <span className="text-muted">•</span>
                <span>
                  {awayName || "Visitante"} {trendLabel(m.away_trend)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </Modal>
    </div>
  );
}
