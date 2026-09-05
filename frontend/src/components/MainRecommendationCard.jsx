import { Flag, Star } from "lucide-react";

function Stars({ count }) {
  return (
    <div className="flex justify-center gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star key={i} size={13} className={i < count ? "fill-yellow-400 text-yellow-400" : "text-border"} />
      ))}
    </div>
  );
}

export default function MainRecommendationCard({ recommendation }) {
  if (!recommendation) {
    return (
      <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
        <div className="text-sm font-medium text-slate-200 mb-2 flex items-center gap-2">
          <Flag size={15} className="text-muted" /> RECOMENDAÇÃO PRINCIPAL
        </div>
        <p className="text-sm text-muted">
          Aguardando minutos suficientes de jogo (mínimo 10') para gerar a primeira recomendação desta partida.
        </p>
      </div>
    );
  }

  const r = recommendation;
  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <span className="text-sm font-medium text-slate-200 flex items-center gap-2">
          <Flag size={15} className="text-muted" /> RECOMENDAÇÃO PRINCIPAL
        </span>
        <span className="bg-accentdim text-accent text-xs font-semibold px-2.5 py-1 rounded-md shrink-0">FORTE</span>
      </div>

      <div className="bg-accentdim/40 border border-accent/30 rounded-lg p-4 mb-4">
        <div className="flex items-center gap-2 text-accent font-medium mb-1">
          <Flag size={14} />
          {r.team_focus || "Partida"}
        </div>
        <div className="text-lg font-semibold text-slate-50">{r.selection}</div>
      </div>

      <div className="grid grid-cols-3 gap-3 text-center mb-4">
        <div>
          <div className="text-[11px] text-muted mb-1">ODD ATUAL</div>
          <div className="text-lg font-semibold text-slate-100">{r.odd.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-[11px] text-muted mb-1">PROB. ESTIMADA</div>
          <div className="text-lg font-semibold text-slate-100">{Math.round(r.estimated_probability * 100)}%</div>
        </div>
        <div>
          <div className="text-[11px] text-muted mb-1">PROB. IMPLÍCITA</div>
          <div className="text-lg font-semibold text-slate-100">{Math.round(r.implied_probability * 100)}%</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 text-center mb-4">
        <div>
          <div className="text-[11px] text-muted mb-1">VALUE BET</div>
          <div className={`text-sm font-semibold ${r.is_value_bet ? "text-accent" : "text-slate-400"}`}>
            {r.is_value_bet ? "SIM" : "NÃO"}
          </div>
        </div>
        <div>
          <div className="text-[11px] text-muted mb-1">CONFIANÇA</div>
          <Stars count={r.confidence_stars} />
        </div>
        <div>
          <div className="text-[11px] text-muted mb-1">EV (VALOR ESPERADO)</div>
          <div className={`text-sm font-semibold ${r.expected_value >= 0 ? "text-accent" : "text-red-400"}`}>
            {r.expected_value >= 0 ? "+" : ""}
            {r.expected_value.toFixed(1)}%
          </div>
        </div>
      </div>

      <div className="border-t border-border pt-3">
        <div className="text-xs font-medium text-muted mb-1">JUSTIFICATIVA</div>
        <p className="text-xs text-slate-300 leading-relaxed">{r.justification}</p>
      </div>
    </div>
  );
}
