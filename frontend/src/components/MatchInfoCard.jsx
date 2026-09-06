import { useEffect, useState } from "react";
import { CalendarClock, Trophy, UserCog } from "lucide-react";
import { ApiClient } from "../api/client";

// Card "Visão Geral" com dados fixos da partida (data/hora, campeonato,
// árbitro) e o histórico de confrontos diretos (H2H) entre os dois times.
//
// NÃO inclui "onde assistir" (canal de TV/streaming) - verificado via
// script de diagnóstico (backend/inspect_broadcast.py) que a resposta da
// API-Football não traz nenhum campo desse tipo; esse dado normalmente
// vem de um provedor de guia de programação, fora do escopo de uma API de
// estatísticas esportivas.
//
// O árbitro é obtido reaproveitando o MESMO endpoint /lineups que a tela
// "Escalações" já usa (o campo referee vem de lá, junto da escalação) -
// evita criar uma chamada de API duplicada só pra esse nome.

function parseUtcTimestamp(isoLike) {
  if (!isoLike) return null;
  const hasTz = /[zZ]|[+-]\d\d:\d\d$/.test(isoLike);
  const date = new Date(hasTz ? isoLike : `${isoLike}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatKickoff(date) {
  if (!date) return "Não informado";
  return date.toLocaleString("pt-BR", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function H2HRow({ item }) {
  const date = parseUtcTimestamp(item.date);
  return (
    <div className="py-2 border-b border-border last:border-0">
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="text-slate-300 truncate flex-1 text-right">{item.home_name}</span>
        <span className="shrink-0 px-2 py-0.5 rounded bg-panel2 text-slate-100 font-medium text-xs">
          {item.home_goals ?? "-"} - {item.away_goals ?? "-"}
        </span>
        <span className="text-slate-300 truncate flex-1">{item.away_name}</span>
      </div>
      <div className="text-[11px] text-muted text-center mt-0.5 truncate">
        {date ? formatKickoff(date) : "Data não informada"}
        {item.league_name ? ` • ${item.league_name}` : ""}
      </div>
    </div>
  );
}

export default function MatchInfoCard({ matchId, match }) {
  const [h2h, setH2h] = useState([]);
  const [referee, setReferee] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!matchId) {
      setH2h([]);
      setReferee(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    Promise.all([
      ApiClient.getH2H(matchId).catch(() => ({ matches: [] })),
      ApiClient.getLineups(matchId).catch(() => ({ referee: null })),
    ]).then(([h2hData, lineupData]) => {
      if (cancelled) return;
      setH2h(Array.isArray(h2hData?.matches) ? h2hData.matches : []);
      setReferee(lineupData?.referee || null);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [matchId]);

  if (!match) return null;
  const kickoff = parseUtcTimestamp(match.kickoff_at);

  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pb-4 mb-4 border-b border-border">
        <div className="flex items-center gap-2">
          <CalendarClock size={16} className="text-muted shrink-0" />
          <div>
            <div className="text-[11px] text-muted">Data e hora</div>
            <div className="text-sm text-slate-200">{formatKickoff(kickoff)}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Trophy size={16} className="text-muted shrink-0" />
          <div>
            <div className="text-[11px] text-muted">Campeonato</div>
            <div className="text-sm text-slate-200 truncate">
              {match.league?.name || "Não informado"}
              {match.round ? ` — ${match.round}` : ""}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <UserCog size={16} className="text-muted shrink-0" />
          <div>
            <div className="text-[11px] text-muted">Árbitro</div>
            <div className="text-sm text-slate-200 truncate">
              {loading ? "Carregando..." : referee || "Não informado"}
            </div>
          </div>
        </div>
      </div>

      <div className="text-sm font-medium text-slate-200 mb-2">H2H PRÉ-JOGO</div>
      {loading ? (
        <p className="text-sm text-muted py-2">Carregando confrontos diretos...</p>
      ) : h2h.length === 0 ? (
        <p className="text-sm text-muted py-2">Nenhum confronto direto recente encontrado entre os dois times.</p>
      ) : (
        <div>
          {h2h.map((item) => (
            <H2HRow key={item.fixture_api_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
