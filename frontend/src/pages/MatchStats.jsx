import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiClient } from "../api/client";
import Header from "../components/Header";
import LiveMatchCard from "../components/LiveMatchCard";
import { StatRow } from "../components/StatBar";

// Mesmo intervalo de polling das outras telas ao vivo (Dados do Jogo,
// Partidas Ao Vivo) - le do banco local via nosso backend, sem custo de
// API (ver docstring de GET /api/matches/{id}/stat-comparison).
const POLL_MS = 15000;

// null = acumulado do jogo todo. Os demais recalculam so pra essa janela
// recente (ver app/services/stat_window_service.py no backend).
const WINDOWS = [
  { label: "Jogo todo", value: null },
  { label: "Últ. 5min", value: 5 },
  { label: "Últ. 10min", value: 10 },
  { label: "Últ. 15min", value: 15 },
];

function formatClock(date) {
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function MatchStats({ selectedLeague, onLeaguesChange, onOpenSidebar }) {
  const [liveMatches, setLiveMatches] = useState([]);
  const [selectedMatchId, setSelectedMatchId] = useState(null);
  const [windowMinutes, setWindowMinutes] = useState(null);
  const [comparison, setComparison] = useState(null);
  // So pra alimentar o LiveMatchCard (placar + barra de posse) no topo da
  // tela - o mesmo cabecalho ja usado em Partidas Ao Vivo e Dados do Jogo,
  // pra essa tela nao ficar so com barras de estatistica sem contexto
  // nenhum de como a partida esta agora. Leitura pura do banco local, sem
  // custo de API (mesmo endpoint que Dados do Jogo ja usa).
  const [latestSnapshot, setLatestSnapshot] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(formatClock(new Date()));
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState("");

  // Mesmo motivo documentado em LiveMatches.jsx/MatchData.jsx: o polling
  // automatico precisa sempre ler o id e a janela MAIS RECENTES escolhidos,
  // nao o valor "congelado" no momento em que o efeito foi montado.
  const selectedMatchIdRef = useRef(selectedMatchId);
  const windowMinutesRef = useRef(windowMinutes);
  useEffect(() => {
    selectedMatchIdRef.current = selectedMatchId;
  }, [selectedMatchId]);
  useEffect(() => {
    windowMinutesRef.current = windowMinutes;
  }, [windowMinutes]);

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

  const loadComparison = useCallback(async (matchId, window) => {
    if (!matchId) {
      setComparison(null);
      return;
    }
    const data = await ApiClient.getStatComparison(matchId, window).catch(() => null);
    setComparison(data);
  }, []);

  const loadLatestSnapshot = useCallback(async (matchId) => {
    if (!matchId) {
      setLatestSnapshot(null);
      return;
    }
    const raw = await ApiClient.getSnapshots(matchId).catch(() => []);
    const list = Array.isArray(raw) ? raw : [];
    setLatestSnapshot(list.length ? list[list.length - 1] : null);
  }, []);

  const loadAll = useCallback(async () => {
    try {
      setLoadError("");
      const matches = await loadLiveMatches();
      const currentId = selectedMatchIdRef.current;
      const targetId = matches.some((m) => m.id === currentId) ? currentId : matches[0]?.id ?? null;
      await Promise.all([loadComparison(targetId, windowMinutesRef.current), loadLatestSnapshot(targetId)]);
      setLastUpdate(formatClock(new Date()));
    } catch {
      setLoadError("Não foi possível conectar ao backend. Verifique se o servidor FastAPI está rodando.");
    }
  }, [loadLiveMatches, loadComparison, loadLatestSnapshot]);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadComparison(selectedMatchId, windowMinutes);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMatchId, windowMinutes]);

  useEffect(() => {
    loadLatestSnapshot(selectedMatchId);
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

  const rows = comparison?.rows ?? [];
  // Mesmo "matchForCard" de LiveMatches.jsx/MatchData.jsx - alimenta o
  // LiveMatchCard reaproveitado como cabecalho desta tela.
  const matchForCard = selectedMatch
    ? {
        ...selectedMatch,
        possessionHome: latestSnapshot ? Math.round(latestSnapshot.possession_home) : 50,
        periodLabel:
          selectedMatch.status === "HT" ? "Intervalo" : selectedMatch.status === "2H" ? "2º TEMPO" : "1º TEMPO",
      }
    : null;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <Header
        lastUpdate={lastUpdate}
        onRefresh={handleRefresh}
        refreshing={refreshing}
        onOpenSidebar={onOpenSidebar}
        title="COMPARATIVO DETALHADO"
        subtitle="Casa x fora, com opção de olhar só os últimos minutos em vez do jogo todo"
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
            <div className="flex items-center justify-center gap-2 flex-wrap mb-4">
              {WINDOWS.map((w) => (
                <button
                  key={w.label}
                  onClick={() => setWindowMinutes(w.value)}
                  className={`text-xs font-medium px-3 py-1.5 rounded-full border ${
                    windowMinutes === w.value
                      ? "border-accent text-accent bg-accentdim"
                      : "border-border text-muted hover:text-slate-200"
                  }`}
                >
                  {w.label}
                </button>
              ))}
            </div>

            {comparison && windowMinutes != null && (
              <p className="text-center text-[11px] text-muted mb-4">
                Considerando do minuto {comparison.from_minute}' ao {comparison.to_minute}'
                {comparison.from_minute === 0 && comparison.to_minute < windowMinutes
                  ? " (a partida ainda não tem histórico suficiente para a janela completa - mostrando desde o início)"
                  : ""}
              </p>
            )}

            <div className="space-y-3">
              {rows.map((r) => (
                <StatRow key={r.key} label={r.label} home={r.home} away={r.away} statKey={r.key} />
              ))}
              {rows.length === 0 && (
                <p className="text-center text-sm text-muted py-6">
                  Ainda sem estatísticas coletadas para essa partida - a primeira coleta acontece em até 5
                  minutos após ela entrar em observação.
                </p>
              )}
            </div>
          </div>
          </>
        ) : (
          <div className="bg-panel border border-border rounded-xl p-10 text-center">
            <p className="text-slate-200 font-medium mb-1">Nenhuma partida ao vivo monitorada no momento</p>
            <p className="text-sm text-muted">
              Assim que uma partida entrar em observação, o comparativo detalhado aparece aqui.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
