import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiClient } from "../api/client";
import Header from "../components/Header";
import LiveMatchCard from "../components/LiveMatchCard";

// Le do banco local via nosso backend - nao consome cota da API-Football
// (os snapshots ja foram coletados antes pelo ciclo de 5 min, ver
// services/collector.py). So mostra o que ja esta salvo.
const POLL_MS = 15000;
const PAGE_SIZE = 12;

// Mesma logica ja usada em MainRecommendationCard/OtherRecommendations: o
// backend manda captured_at como datetime "naive" em UTC (datetime.utcnow()
// no Python), sem sufixo de fuso - sem forcar "Z" aqui, o Date() do JS leria
// como horario LOCAL do navegador em vez de UTC, e o horario exibido saira
// errado pelo fuso do usuario.
function parseUtcTimestamp(isoLike) {
  if (!isoLike) return null;
  const hasTz = /[zZ]|[+-]\d\d:\d\d$/.test(isoLike);
  const date = new Date(hasTz ? isoLike : `${isoLike}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatClock(date) {
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// Mesmo helper de paginacao do RecommendationHistoryTable (ver aquele
// arquivo para o raciocinio completo) - duplicado aqui de proposito, no
// mesmo padrao ja usado no projeto para pequenos helpers de UI (ex:
// parseUtcTimestamp acima), para nao criar um acoplamento entre paginas por
// causa de uma funcao de 15 linhas.
function buildPageList(current, total) {
  const pages = [];
  const WINDOW = 1;
  let lastAdded = 0;
  for (let p = 1; p <= total; p++) {
    const isEdge = p === 1 || p === total;
    const isNearCurrent = Math.abs(p - current) <= WINDOW;
    if (isEdge || isNearCurrent) {
      if (lastAdded && p - lastAdded > 1) pages.push("...");
      pages.push(p);
      lastAdded = p;
    }
  }
  return pages;
}

// Celula "casa / fora" - mesma convencao de cor do DetailedStatsPanel
// (time da casa em azul, visitante em vermelho) para ficar reconhecivel em
// qualquer tela do app.
function HomeAwayCell({ home, away, decimals = 0 }) {
  const fmt = (v) => (typeof v === "number" ? v.toFixed(decimals) : v ?? "-");
  return (
    <span className="whitespace-nowrap">
      <span className="text-blue-400">{fmt(home)}</span>
      <span className="text-muted"> / </span>
      <span className="text-red-400">{fmt(away)}</span>
    </span>
  );
}

export default function MatchData({ selectedLeague, onLeaguesChange, onOpenSidebar }) {
  const [liveMatches, setLiveMatches] = useState([]);
  const [selectedMatchId, setSelectedMatchId] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(formatClock(new Date()));
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [page, setPage] = useState(1);

  // O polling automatico precisa sempre ler o id MAIS RECENTE selecionado,
  // nao o valor "congelado" no momento em que o efeito foi montado (mesmo
  // motivo documentado em LiveMatches.jsx/Dashboard.jsx).
  const selectedMatchIdRef = useRef(selectedMatchId);
  useEffect(() => {
    selectedMatchIdRef.current = selectedMatchId;
  }, [selectedMatchId]);

  const filteredMatches = useMemo(
    () => liveMatches.filter((m) => selectedLeague === "Todas" || m.league?.name === selectedLeague),
    [liveMatches, selectedLeague]
  );

  const selectedMatch = useMemo(
    () => filteredMatches.find((m) => m.id === selectedMatchId) || null,
    [filteredMatches, selectedMatchId]
  );

  useEffect(() => {
    if (!filteredMatches.some((m) => m.id === selectedMatchId)) {
      setSelectedMatchId(filteredMatches[0]?.id ?? null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filteredMatches]);

  // Troca de partida sempre volta pra primeira pagina - senao a pagina 3 de
  // um jogo longo podia ficar "vazia" ao trocar pra um jogo que comecou ha
  // pouco e so tem 2 snapshots ainda.
  useEffect(() => {
    setPage(1);
  }, [selectedMatchId]);

  const loadLiveMatches = useCallback(async () => {
    const raw = await ApiClient.listLiveMatches();
    const matches = Array.isArray(raw) ? raw : [];
    setLiveMatches(matches);
    const currentId = selectedMatchIdRef.current;
    if (matches.length > 0 && !matches.some((m) => m.id === currentId)) {
      setSelectedMatchId(matches[0].id);
    }
    if (matches.length === 0 && currentId !== null) setSelectedMatchId(null);
    if (onLeaguesChange) {
      const uniqueLeagues = Array.from(
        new Set(matches.map((m) => m.league?.name).filter(Boolean))
      ).sort((a, b) => a.localeCompare(b, "pt-BR"));
      onLeaguesChange(uniqueLeagues);
    }
    return matches;
  }, [onLeaguesChange]);

  const loadSnapshots = useCallback(async (matchId) => {
    if (!matchId) {
      setSnapshots([]);
      return;
    }
    const raw = await ApiClient.getSnapshots(matchId).catch(() => []);
    setSnapshots(Array.isArray(raw) ? raw : []);
  }, []);

  const loadAll = useCallback(async () => {
    try {
      setLoadError("");
      const matches = await loadLiveMatches();
      const currentId = selectedMatchIdRef.current;
      const targetId = matches.some((m) => m.id === currentId) ? currentId : matches[0]?.id ?? null;
      await loadSnapshots(targetId);
      setLastUpdate(formatClock(new Date()));
    } catch {
      setLoadError("Não foi possível conectar ao backend. Verifique se o servidor FastAPI está rodando.");
    }
  }, [loadLiveMatches, loadSnapshots]);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadSnapshots(selectedMatchId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMatchId]);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await loadAll();
    } catch {
      setLoadError("Falha ao atualizar - o backend pode estar offline.");
    } finally {
      setRefreshing(false);
    }
  }

  // O backend devolve em ordem crescente de minuto (ver GET
  // /api/matches/{id}/snapshots) - aqui invertemos pra mostrar o snapshot
  // mais recente primeiro, que e o que mais interessa checar ("salvou
  // certo agora ha pouco?") sem precisar rolar ate o fim da tabela.
  const orderedSnapshots = useMemo(() => [...snapshots].reverse(), [snapshots]);
  const latestSnapshot = orderedSnapshots[0] || null;
  // Mesmo "matchForCard" montado em LiveMatches.jsx - reusa o LiveMatchCard
  // (placar + barra de posse) pra essa tela nao ficar so com uma tabela
  // crua, sem contexto nenhum de como a partida esta agora.
  const matchForCard = selectedMatch
    ? {
        ...selectedMatch,
        possessionHome: latestSnapshot ? Math.round(latestSnapshot.possession_home) : 50,
        periodLabel:
          selectedMatch.status === "HT" ? "Intervalo" : selectedMatch.status === "2H" ? "2º TEMPO" : "1º TEMPO",
      }
    : null;
  const totalPages = Math.max(1, Math.ceil(orderedSnapshots.length / PAGE_SIZE));
  const safePage = Math.min(Math.max(page, 1), totalPages);
  const start = (safePage - 1) * PAGE_SIZE;
  const pageRows = orderedSnapshots.slice(start, start + PAGE_SIZE);
  const pageList = buildPageList(safePage, totalPages);

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <Header
        lastUpdate={lastUpdate}
        onRefresh={handleRefresh}
        refreshing={refreshing}
        onOpenSidebar={onOpenSidebar}
        title="DADOS DO JOGO"
        subtitle="Cada linha é um snapshot salvo pelo coletor, com o minuto exato da partida"
      />

      <div className="flex-1 overflow-y-auto overflow-x-hidden px-4 sm:px-6 py-4 sm:py-5 space-y-5">
        {loadError && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-300 text-sm rounded-lg px-4 py-3">
            {loadError}
          </div>
        )}

        {filteredMatches.length > 1 && (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {filteredMatches.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelectedMatchId(m.id)}
                className={`shrink-0 flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border ${
                  m.id === selectedMatchId
                    ? "border-accent text-accent bg-accentdim"
                    : "border-border text-muted hover:text-slate-200"
                }`}
              >
                <span className="relative flex w-1.5 h-1.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                  <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-red-500" />
                </span>
                {m.home_team.name} x {m.away_team.name} ({m.elapsed_minutes}')
              </button>
            ))}
          </div>
        )}

        {selectedMatch ? (
          <>
          <LiveMatchCard match={matchForCard} hideTabs />
          <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
            <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
              <span className="text-sm font-medium text-slate-200">
                {selectedMatch.home_team.name} x {selectedMatch.away_team.name}
              </span>
              <span className="text-xs text-muted">
                {orderedSnapshots.length} snapshot{orderedSnapshots.length === 1 ? "" : "s"} salvo
                {orderedSnapshots.length === 1 ? "" : "s"}
              </span>
            </div>
            <p className="text-xs text-muted mb-4">
              <span className="text-blue-400">{selectedMatch.home_team.name}</span> /{" "}
              <span className="text-red-400">{selectedMatch.away_team.name}</span> em cada coluna "casa / fora"
              abaixo
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[820px]">
                <thead>
                  <tr className="text-muted text-xs">
                    <th className="text-left font-normal pb-2">MINUTO</th>
                    <th className="text-left font-normal pb-2">HORÁRIO SALVO</th>
                    <th className="text-right font-normal pb-2">PLACAR</th>
                    <th className="text-right font-normal pb-2">POSSE %</th>
                    <th className="text-right font-normal pb-2">FINALIZAÇÕES</th>
                    <th className="text-right font-normal pb-2">NO ALVO</th>
                    <th className="text-right font-normal pb-2">ESCANTEIOS</th>
                    <th className="text-right font-normal pb-2">CARTÕES A/V</th>
                    <th className="text-right font-normal pb-2">FALTAS</th>
                    <th className="text-right font-normal pb-2">xG</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {pageRows.map((s) => {
                    const captured = parseUtcTimestamp(s.captured_at);
                    return (
                      <tr key={s.id}>
                        <td className="py-2.5 text-slate-200 font-medium whitespace-nowrap">{s.minute}'</td>
                        <td className="py-2.5 text-slate-300 whitespace-nowrap">
                          {captured ? formatClock(captured) : "-"}
                        </td>
                        <td className="py-2.5 text-right text-slate-100 font-medium whitespace-nowrap">
                          {s.goals_home} - {s.goals_away}
                        </td>
                        <td className="py-2.5 text-right">
                          <HomeAwayCell home={s.possession_home} away={s.possession_away} />
                        </td>
                        <td className="py-2.5 text-right">
                          <HomeAwayCell home={s.total_shots_home} away={s.total_shots_away} />
                        </td>
                        <td className="py-2.5 text-right">
                          <HomeAwayCell home={s.shots_on_target_home} away={s.shots_on_target_away} />
                        </td>
                        <td className="py-2.5 text-right">
                          <HomeAwayCell home={s.corners_home} away={s.corners_away} />
                        </td>
                        <td className="py-2.5 text-right whitespace-nowrap">
                          <span className="text-yellow-400">
                            {s.yellow_cards_home}/{s.yellow_cards_away}
                          </span>
                          <span className="text-muted"> · </span>
                          <span className="text-red-400">
                            {s.red_cards_home}/{s.red_cards_away}
                          </span>
                        </td>
                        <td className="py-2.5 text-right">
                          <HomeAwayCell home={s.fouls_home} away={s.fouls_away} />
                        </td>
                        <td className="py-2.5 text-right">
                          <HomeAwayCell home={s.xg_home} away={s.xg_away} decimals={2} />
                        </td>
                      </tr>
                    );
                  })}
                  {orderedSnapshots.length === 0 && (
                    <tr>
                      <td colSpan={10} className="py-6 text-center text-muted text-sm">
                        Nenhum snapshot salvo ainda para essa partida - o coletor grava o primeiro assim que ela
                        atinge o próximo ciclo de coleta.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-1.5 flex-wrap mt-4">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={safePage === 1}
                  className="text-xs font-medium px-3 py-1.5 rounded-md bg-panel2 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110"
                >
                  « Anterior
                </button>
                {pageList.map((p, idx) =>
                  p === "..." ? (
                    <span key={`ellipsis-${idx}`} className="text-xs text-muted px-1">
                      ...
                    </span>
                  ) : (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`text-xs font-medium w-7 h-7 rounded-md shrink-0 ${
                        p === safePage ? "bg-accent text-panel" : "bg-panel2 text-slate-300 hover:brightness-110"
                      }`}
                    >
                      {p}
                    </button>
                  )
                )}
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={safePage === totalPages}
                  className="text-xs font-medium px-3 py-1.5 rounded-md bg-panel2 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110"
                >
                  Próxima »
                </button>
              </div>
            )}
          </div>
          </>
        ) : (
          <div className="bg-panel border border-border rounded-xl p-10 text-center">
            <p className="text-slate-200 font-medium mb-1">Nenhuma partida ao vivo monitorada no momento</p>
            <p className="text-sm text-muted">
              Assim que uma partida entrar em observação, os snapshots salvos a cada ciclo de coleta aparecem
              aqui, minuto a minuto.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
