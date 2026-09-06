import { useState } from "react";
import { Flag, Star } from "lucide-react";
import Modal from "./Modal";

// Mesma logica do MainRecommendationCard: mostra se a odd exibida veio de
// verdade do mercado ao vivo (/odds/live) ou e uma estimativa - null
// (registro antigo, gravado antes dessa coluna existir) nao mostra nada.
function OddSourceTag({ isLive }) {
  if (isLive == null) return null;
  return (
    <span
      className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${
        isLive ? "bg-accentdim text-accent" : "bg-yellow-500/10 text-yellow-400"
      }`}
      title={
        isLive
          ? "Odd real, vinda do mercado ao vivo agora."
          : "Sem cotação ao vivo disponível pra esse mercado agora - odd estimada a partir da probabilidade calculada."
      }
    >
      {isLive ? "AO VIVO" : "ESTIMADA"}
    </span>
  );
}

function Stars({ count }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star key={i} size={12} className={i < count ? "fill-yellow-400 text-yellow-400" : "text-border"} />
      ))}
    </div>
  );
}

function FullRecommendationCard({ r }) {
  return (
    <div className="border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="flex items-center gap-2 text-sm font-medium text-slate-200">
          <Flag size={13} className="text-muted" />
          {r.team_focus ? `${r.team_focus} - ${r.selection}` : r.selection}
        </span>
        {r.is_primary && (
          <span className="bg-accentdim text-accent text-[10px] font-semibold px-2 py-0.5 rounded-md shrink-0">
            PRINCIPAL
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center mb-3">
        <div>
          <div className="text-[10px] text-muted mb-0.5 flex items-center justify-center gap-1">
            ODD
            <OddSourceTag isLive={r.odd_is_live} />
          </div>
          <div className="text-sm font-semibold text-slate-100">{r.odd.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-[10px] text-muted mb-0.5">PROB. EST.</div>
          <div className="text-sm font-semibold text-slate-100">{Math.round(r.estimated_probability * 100)}%</div>
        </div>
        <div>
          <div className="text-[10px] text-muted mb-0.5">EV</div>
          <div className={`text-sm font-semibold ${r.expected_value >= 0 ? "text-accent" : "text-red-400"}`}>
            {r.expected_value >= 0 ? "+" : ""}
            {r.expected_value.toFixed(1)}%
          </div>
        </div>
        <div>
          <div className="text-[10px] text-muted mb-0.5">CONFIANÇA</div>
          <div className="flex justify-center">
            <Stars count={r.confidence_stars} />
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 mb-2">
        <span
          className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
            r.is_value_bet ? "bg-accentdim text-accent" : "bg-panel2 text-muted"
          }`}
        >
          {r.is_value_bet ? "VALUE BET" : "SEM VALUE"}
        </span>
      </div>
      {r.justification && <p className="text-xs text-slate-400 leading-relaxed">{r.justification}</p>}
    </div>
  );
}

export default function OtherRecommendations({ recommendations, allRecommendations }) {
  const [showModal, setShowModal] = useState(false);
  const fullList = allRecommendations && allRecommendations.length > 0 ? allRecommendations : recommendations;

  if (!recommendations || recommendations.length === 0) return null;

  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="text-sm font-medium text-slate-200 mb-3">OUTRAS RECOMENDAÇÕES</div>
      <div className="space-y-2.5">
        {recommendations.map((r) => (
          <div key={r.id} className="flex items-center justify-between flex-wrap gap-1.5 text-sm">
            <span className="flex items-center gap-2 text-slate-300 min-w-0">
              <Flag size={13} className="text-muted shrink-0" />
              <span className="truncate">
                {r.team_focus ? `${r.team_focus} - ${r.selection}` : r.selection}
              </span>
            </span>
            <span className="flex items-center gap-2 shrink-0">
              <span className="text-slate-200 flex items-center gap-1">
                Odd: {r.odd.toFixed(2)}
                <OddSourceTag isLive={r.odd_is_live} />
              </span>
              <span
                className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                  r.confidence_stars >= 4
                    ? "bg-accentdim text-accent"
                    : "bg-yellow-500/10 text-yellow-400"
                }`}
              >
                {r.confidence_stars >= 4 ? "ALTA" : "MÉDIA"}
              </span>
            </span>
          </div>
        ))}
      </div>
      <button
        onClick={() => setShowModal(true)}
        className="w-full mt-4 bg-accentdim text-accent text-sm font-medium py-2 rounded-lg hover:brightness-110"
      >
        VER TODAS RECOMENDAÇÕES
      </button>

      <Modal
        open={showModal}
        onClose={() => setShowModal(false)}
        title="Todas as recomendações desta partida"
        widthClass="max-w-2xl"
      >
        {fullList.length === 0 ? (
          <p className="text-sm text-muted">Nenhuma recomendação disponível no momento.</p>
        ) : (
          <div className="space-y-3">
            {fullList.map((r) => (
              <FullRecommendationCard key={r.id} r={r} />
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
}
