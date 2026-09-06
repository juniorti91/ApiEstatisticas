import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { ApiClient } from "../api/client";
import Header from "../components/Header";
import LiveMatchCard from "../components/LiveMatchCard";

// Mesmo intervalo das outras telas ao vivo - so leitura do banco local via
// nosso backend (snapshots + TeamForm ja existentes), sem chamada nova a
// API-Football (ver app/services/prognostics_service.py).
const POLL_MS = 15000;

const TREND_INFO = {
  subindo_forte: { arrow: "↑↑", label: "subindo forte", color: "text-accent" },
  subindo: { arrow: "↑", label: "subindo", color: "text-accent" },
  estavel: { arrow: "→", label: "estável", color: "text-muted" },
  caindo: { arrow: "↓", label: "caindo", color: "text-red-400" },
  caindo_forte: { arrow: "↓↓", label: "caindo forte", color: "text-red-400" },
  indisponivel: { arrow: "—", label: "sem dado suficiente ainda", color: "text-muted" },
};

function formatClock(date) {
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function pct(value) {
  return `${Math.round(value * 100)}%`;
}

function WinProbabilityBar({ winProbability, homeName, awayName }) {
  const home = Math.round(winProbability.home * 100);
  const draw = Math.round(winProbability.draw * 100);
  const away = Math.max(0, 100 - home - draw); // garante que some exatamente 100 mesmo com arredondamento
  return (
    <div>
      <div className="flex h-3 rounded-full overflow-hidden bg-panel2">
        <div className="h-full bg-blue-500" style={{ width: `${home}%` }} title={`${homeName}: ${home}%`} />
        <div className="h-full bg-slate-500" style={{ width: `${draw}%` }} title={`Empate: ${draw}%`} />
        <div className="h-full bg-red-500" style={{ width: `${away}%` }} title={`${awayName}: ${away}%`} />
      </div>
      <div className="flex justify-between mt-2 text-xs">
        <div className="text-blue-400 font-medium">
          {homeName} <span className="text-slate-200">{home}%</span>
        </div>
        <div className="text-muted font-medium">
          Empate <span className="text-slate-200">{draw}%</span>
        </div>
        <div className="text-red-400 font-medium text-right">
          {awayName} <span className="text-slate-200">{away}%</span>
        </div>
      </div>
    </div>
  );
}

function MomentumBar({ label, value, delta, trend, color }) {
  const trendInfo = TREND_INFO[trend] || TREND_INFO.indisponivel;
  const safeValue = value ?? 0;
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-slate-300">{label}</span>
        <span className="flex items-center gap-1">
          <span className="text-slate-200 font-medium">{value != null ? Math.round(value) : "—"}</span>
          {delta != null && (
            <span className={`${trendInfo.color} text-[11px]`}>
              {trendInfo.arrow} {delta > 0 ? "+" : ""}
              {delta}
            </span>
          )}
        </span>
      </div>
      <div className="h-2 rounded-full bg-panel2 overflow-hidden">
        <div className="h-full rounded-full transition-[width] duration-700" style={{ width: `${safeValue}%`, backgroundColor: color }} />
      </div>
      <div className={`text-[10px] mt-0.5 ${trendInfo.color}`}>{trendInfo.label}</div>
    </div>
  );
}

function AnomalyRow({ label, homePct, awayPct }) {
  function badge(value) {
    if (value == null) {
      return <span className="text-muted text-xs">sem média histórica</span>;
    }
    const isUp = value > 0;
    const Icon = value === 0 ? Minus : isUp ? TrendingUp : TrendingDown;
    const color = value === 0 ? "text-muted" : isUp ? "text-accent" : "text-red-400";
    return (
      <span className={`inline-flex items-center gap-1 text-xs font-medium ${color}`}>
        <Icon size={12} />
        {value > 0 ? "+" : ""}
        {value}%
      </span>
    );
  }

  return (
    <div className="flex items-center justify-between py-2 border-b border-border last:border-0 text-sm">
      <div className="w-24 text-right">{badge(homePct)}</div>
      <div className="flex-1 text-center text-slate-300 truncate px-2">{label}</div>
      <div className="w-24">{badge(awayPct)}</div>
    </div>
  );
}

export default function Prognostics({ selectedLeague, onLeaguesChange, onOpenSidebar }) {
  const [liveMatches, setLiveMatches] = useState([]);
  const [selectedMatchId, setSelectedMatchId] = useState(null);
  const [prognostics, setPrognostics] = useState(null);
  const [latestSnapshot, setLatestSnapshot] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(formatClock(new Date()));
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState("");

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

  const loadPrognostics = useCallback(async (matchId) => {
    if (!matchId) {
      setPrognostics(null);
      return;
    }
    const data = await ApiClient.getPrognostics(matchId).catch(() => null);
    setPrognostics(data);
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
      await Promise.all([loadPrognostics(targetId), loadLatestSnapshot(targetId)]);
      setLastUpdate(formatClock(new Date()));
    } catch {
      setLoadError("Não foi possível conectar ao backend. Verifique se o servidor FastAPI está rodando.");
    }
  }, [loadLiveMatches, loadPrognostics, loadLatestSnapshot]);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadPrognostics(selectedMatchId);
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

  const matchForCard = selectedMatch
    ? {
        ...selectedMatch,
        possessionHome: latestSnapshot ? Math.round(latestSnapshot.possession_home) : 50,
        periodLabel:
          selectedMatch.status === "HT" ? "Intervalo" : selectedMatch.status === "2H" ? "2º TEMPO" : "1º TEMPO",
      }
    : null;

  const homeName = selectedMatch?.home_team?.name || "Casa";
  const awayName = selectedMatch?.away_team?.name || "Fora";

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <Header
        lastUpdate={lastUpdate}
        onRefresh={handleRefresh}
        refreshing={refreshing}
        onOpenSidebar={onOpenSidebar}
        title="PROGNÓSTICOS"
        subtitle="Probabilidade de vitória, de gol e índice de momentum - estimados a partir dos dados que já coletamos"
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

        {selectedMatch && prognostics ? (
          <>
            <LiveMatchCard match={matchForCard} hideTabs />

            <p className="text-[11px] text-muted bg-panel2 border border-border rounded-lg px-3 py-2">
              Estes números são estimativas calculadas por um modelo estatístico próprio (Poisson, combinando o
              ritmo ao vivo com a média recente de cada time) — não são odds de casa de apostas nem previsões
              garantidas.
            </p>

            {prognostics.insufficient_data && (
              <div className="bg-yellow-500/10 border border-yellow-500/30 text-yellow-300 text-sm rounded-lg px-4 py-3">
                Partida ainda no início ({prognostics.minute}') - dados insuficientes para um prognóstico
                confiável ainda. Os números abaixo são só um ponto de partida neutro.
              </div>
            )}

            <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
              <div className="text-sm font-medium text-slate-200 mb-3">PROBABILIDADE DE VITÓRIA</div>
              <WinProbabilityBar winProbability={prognostics.win_probability} homeName={homeName} awayName={awayName} />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
                <div className="text-sm font-medium text-slate-200 mb-3">PRÓXIMO GOL</div>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-blue-400">{homeName}</span>
                  <span className="text-slate-200 font-medium">{pct(prognostics.next_goal.home)}</span>
                </div>
                <div className="h-2 rounded-full bg-panel2 overflow-hidden flex mb-3">
                  <div className="h-full bg-blue-500" style={{ width: pct(prognostics.next_goal.home) }} />
                  <div className="h-full bg-red-500" style={{ width: pct(prognostics.next_goal.away) }} />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-red-400">{awayName}</span>
                  <span className="text-slate-200 font-medium">{pct(prognostics.next_goal.away)}</span>
                </div>
              </div>

              <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
                <div className="text-sm font-medium text-slate-200 mb-3">GOL NOS PRÓXIMOS MINUTOS</div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-muted text-xs">
                      <th className="text-left font-normal pb-2"></th>
                      <th className="text-right font-normal pb-2">Próx. 5min</th>
                      <th className="text-right font-normal pb-2">Próx. 10min</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    <tr>
                      <td className="py-1.5 text-blue-400">{homeName}</td>
                      <td className="py-1.5 text-right text-slate-200">{pct(prognostics.goal_windows.home_5min)}</td>
                      <td className="py-1.5 text-right text-slate-200">{pct(prognostics.goal_windows.home_10min)}</td>
                    </tr>
                    <tr>
                      <td className="py-1.5 text-red-400">{awayName}</td>
                      <td className="py-1.5 text-right text-slate-200">{pct(prognostics.goal_windows.away_5min)}</td>
                      <td className="py-1.5 text-right text-slate-200">{pct(prognostics.goal_windows.away_10min)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-medium text-slate-200">ÍNDICE DE MOMENTUM</div>
                <div className="text-[10px] text-muted">últimos 15min vs os 15min anteriores</div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <MomentumBar
                  label={homeName}
                  value={prognostics.momentum.home}
                  delta={prognostics.momentum.home_delta}
                  trend={prognostics.momentum.home_trend}
                  color="#3b82f6"
                />
                <MomentumBar
                  label={awayName}
                  value={prognostics.momentum.away}
                  delta={prognostics.momentum.away_delta}
                  trend={prognostics.momentum.away_trend}
                  color="#ef4444"
                />
              </div>
            </div>

            <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
              <div className="text-sm font-medium text-slate-200 mb-1">COMPARADO À MÉDIA RECENTE</div>
              <p className="text-[11px] text-muted mb-3">
                Ritmo atual projetado para os 90 minutos, comparado à média das últimas partidas de cada time.
              </p>
              {prognostics.anomalies.length === 0 ? (
                <p className="text-sm text-muted py-2 text-center">Sem dados suficientes ainda.</p>
              ) : (
                <div>
                  {prognostics.anomalies.map((row) => (
                    <AnomalyRow key={row.label} label={row.label} homePct={row.home_pct} awayPct={row.away_pct} />
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="bg-panel border border-border rounded-xl p-10 text-center">
            <p className="text-slate-200 font-medium mb-1">Nenhuma partida ao vivo monitorada no momento</p>
            <p className="text-sm text-muted">Assim que uma partida entrar em observação, os prognósticos aparecem aqui.</p>
          </div>
        )}
      </div>
    </div>
  );
}
