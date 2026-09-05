import { TrendingUp } from "lucide-react";

function Delta({ value, suffix = "%" }) {
  if (value === 0) return <span className="text-muted text-xs">sem variação</span>;
  const up = value > 0;
  return (
    <span className={`text-xs flex items-center gap-1 ${up ? "text-accent" : "text-red-400"}`}>
      {up ? "↑" : "↓"} {Math.abs(value).toFixed(1)}
      {suffix} vs período anterior
    </span>
  );
}

export default function PerformanceFooter({ performance }) {
  if (!performance) return null;
  const p = performance;

  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 sm:gap-6">
      <div className="col-span-2 sm:col-span-1">
        <div className="flex items-center gap-2 text-xs text-muted mb-1">
          <TrendingUp size={14} /> PERFORMANCE GERAL
        </div>
        <div className="text-[11px] text-muted">Últimos {p.period_days} dias</div>
      </div>
      <div>
        <div className="text-xs text-muted mb-1">TAXA DE ACERTO</div>
        <div className="text-2xl font-semibold text-slate-100">{p.hit_rate.toFixed(1)}%</div>
        <Delta value={p.hit_rate_delta} />
      </div>
      <div>
        <div className="text-xs text-muted mb-1">ROI (RETORNO)</div>
        <div className={`text-2xl font-semibold ${p.roi >= 0 ? "text-accent" : "text-red-400"}`}>
          {p.roi >= 0 ? "+" : ""}
          {p.roi.toFixed(1)}%
        </div>
        <Delta value={p.roi_delta} />
      </div>
      <div>
        <div className="text-xs text-muted mb-1">LUCRO/PREJUÍZO</div>
        <div className={`text-2xl font-semibold ${p.profit_loss >= 0 ? "text-accent" : "text-red-400"}`}>
          {p.profit_loss >= 0 ? "+" : ""}
          R$ {p.profit_loss.toFixed(2)}
        </div>
        <div className="text-[11px] text-muted">Baseado em stake de R$ {p.stake_base.toFixed(2)} por entrada</div>
      </div>
      <div>
        <div className="text-xs text-muted mb-1">Nº DE RECOMENDAÇÕES</div>
        <div className="text-2xl font-semibold text-slate-100">{p.total_recommendations}</div>
        <div className="text-[11px] text-muted">{p.value_bets_share.toFixed(0)}% eram value bets</div>
      </div>
    </div>
  );
}
