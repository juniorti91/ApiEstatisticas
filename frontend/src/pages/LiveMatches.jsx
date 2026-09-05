import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiClient } from "../api/client";
import Header from "../components/Header";
import LiveMatchCard from "../components/LiveMatchCard";
import DetailedStatsPanel from "../components/DetailedStatsPanel";

// Le do banco local via nosso backend - nao consome cota da API-Football.
const POLL_MS = 15000;
// As estatisticas de jogador (duelos, dribles, notas) custam uma chamada
// de verdade na API-Football a cada vez que sao buscadas (ver
// GET /api/matches/{id}/detailed-stats no backend). Por isso atualizam
// bem mais devagar que o resto da tela enquanto o usuario fica com essa
// partida aberta - nao ha necessidade de fazer isso a cada 15s.
const DETAILED_POLL_MS = 60000;

function formatClock(date) {
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function LiveMatches({ selectedLeague, onLeaguesChange, onOpenSidebar }) {
  const [liveMatches, setLiveMatches] = useState([]);
  const [selectedMatchId, setSelectedMatchId] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [detailedStats, setDetailedStats] = useState(null);
  const [detailedLoading, setDetailedLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(formatClock(new Date()));
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState("");

  // Mesmo motivo do Dashboard: o auto-refresh periodico precisa sempre ler
  // o id MAIS RECENTE selecionado, nao o valor "congelado" no momento em
  // que o efeito foi montado.
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

  const loadDetailedStats = useCallback(async (matchId) => {
    if (!matchId) {
      setDetailedStats(null);
      return;
    }
    setDetailedLoading(true);
    try {
      const data = await ApiClient.getDetailedStats(matchId);
      setDetailedStats(data);
    } catch {
      // Mantem o ultimo dado detalhado valido na tela em vez de sumir com
      // tudo por causa de uma falha pontual (ex: rate limit momentaneo).
    } finally {
      setDetailedLoading(false);
    }
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
    loadDetailedStats(selectedMatchId);
    const interval = setInterval(() => loadDetailedStats(selectedMatchId), DETAILED_POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMatchId]);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await loadAll();
      await loadDetailedStats(selectedMatchIdRef.current);
    } catch {
      setLoadError("Falha ao atualizar - o backend pode estar offline.");
    } finally {
      setRefreshing(false);
    }
  }

  const latestSnapshot = snapshots.length ? snapshots[snapshots.length - 1] : null;

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
        title="PARTIDAS AO VIVO"
        subtitle="Estatísticas completas e em tempo real de cada partida monitorada"
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
          <div className="space-y-5">
            <LiveMatchCard match={matchForCard} hideTabs />
            <DetailedStatsPanel
              homeName={selectedMatch.home_team.name}
              awayName={selectedMatch.away_team.name}
              snapshot={latestSnapshot}
              detailed={detailedStats}
              loading={detailedLoading}
            />
          </div>
        ) : (
          <div className="bg-panel border border-border rounded-xl p-10 text-center">
            <p className="text-slate-200 font-medium mb-1">Nenhuma partida ao vivo monitorada no momento</p>
            <p className="text-sm text-muted">
              Assim que uma partida entrar em observação (automaticamente ou via monitoramento manual no
              Dashboard), ela aparece aqui com as estatísticas completas.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
