import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiClient } from "../api/client";
import Header from "../components/Header";
import { StatRow } from "../components/StatBar";

const POLL_MS = 30000;
const OU_LINES = [0.5, 1.5, 2.5];
const MIN_GAMES = 3;
const MAX_GAMES = 20;
const DEFAULT_GAMES = 5;

function formatClock(date) {
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// Aplica os filtros (quantidade de jogos, so em casa/fora, so na mesma
// competicao) e calcula tudo que a tela mostra - tudo em cima da lista ja
// cacheada que o backend devolve (ver GET /api/teams/{id}/history), sem
// nenhuma chamada nova a API a cada mudanca de filtro: e por isso que os
// filtros reagem na hora, sem precisar de um botao "Aplicar".
function computeStats(rows, { gamesCount, sameVenue, venueIsHome, sameCompetition, leagueApiId }) {
  let pool = rows;
  if (sameCompetition && leagueApiId != null) {
    pool = pool.filter((r) => r.league_api_id === leagueApiId);
  }
  if (sameVenue) {
    pool = pool.filter((r) => r.is_home === venueIsHome);
  }
  // rows ja chega do backend ordenado do mais recente pro mais antigo.
  const used = pool.slice(0, gamesCount);
  const n = used.length;

  let wins = 0,
    draws = 0,
    losses = 0,
    goalsFor = 0,
    goalsAgainst = 0,
    btts = 0;
  const overCounts = Object.fromEntries(OU_LINES.map((l) => [l, 0]));

  for (const m of used) {
    if (m.goals_for > m.goals_against) wins += 1;
    else if (m.goals_for === m.goals_against) draws += 1;
    else losses += 1;
    goalsFor += m.goals_for;
    goalsAgainst += m.goals_against;
    if (m.goals_for > 0 && m.goals_against > 0) btts += 1;
    const total = m.goals_for + m.goals_against;
    for (const line of OU_LINES) {
      if (total > line) overCounts[line] += 1;
    }
  }

  const htUsed = used.filter((m) => m.ht_goals_for != null && m.ht_goals_against != null);
  const htN = htUsed.length;
  let htWins = 0,
    htDraws = 0,
    htLosses = 0,
    htGoalsFor = 0,
    htGoalsAgainst = 0,
    htBtts = 0;
  const htOverCounts = Object.fromEntries(OU_LINES.map((l) => [l, 0]));
  for (const m of htUsed) {
    if (m.ht_goals_for > m.ht_goals_against) htWins += 1;
    else if (m.ht_goals_for === m.ht_goals_against) htDraws += 1;
    else htLosses += 1;
    htGoalsFor += m.ht_goals_for;
    htGoalsAgainst += m.ht_goals_against;
    if (m.ht_goals_for > 0 && m.ht_goals_against > 0) htBtts += 1;
    const total = m.ht_goals_for + m.ht_goals_against;
    for (const line of OU_LINES) {
      if (total > line) htOverCounts[line] += 1;
    }
  }

  return {
    n,
    wins,
    draws,
    losses,
    avgGoalsFor: n ? goalsFor / n : 0,
    avgGoalsAgainst: n ? goalsAgainst / n : 0,
    btts,
    overCounts,
    htN,
    htWins,
    htDraws,
    htLosses,
    avgHtGoalsFor: htN ? htGoalsFor / htN : 0,
    avgHtGoalsAgainst: htN ? htGoalsAgainst / htN : 0,
    htBtts,
    htOverCounts,
  };
}

function Section({ title, note, children }) {
  return (
    <div>
      <div className="flex items-baseline gap-2 mb-2.5">
        <span className="text-xs font-semibold text-muted tracking-wide">{title.toUpperCase()}</span>
        {note && <span className="text-[10px] text-muted">{note}</span>}
      </div>
      <div className="space-y-2.5">{children}</div>
    </div>
  );
}

export default function TeamHistory({ selectedLeague, onLeaguesChange, onOpenSidebar }) {
  const [liveMatches, setLiveMatches] = useState([]);
  const [selectedMatchId, setSelectedMatchId] = useState(null);
  const [homeRows, setHomeRows] = useState([]);
  const [awayRows, setAwayRows] = useState([]);
  const [gamesCount, setGamesCount] = useState(DEFAULT_GAMES);
  const [sameVenue, setSameVenue] = useState(false);
  const [sameCompetition, setSameCompetition] = useState(false);
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

  const loadHistories = useCallback(async (match) => {
    if (!match) {
      setHomeRows([]);
      setAwayRows([]);
      return;
    }
    const [home, away] = await Promise.all([
      ApiClient.getTeamHistory(match.home_team.id).catch(() => []),
      ApiClient.getTeamHistory(match.away_team.id).catch(() => []),
    ]);
    setHomeRows(Array.isArray(home) ? home : []);
    setAwayRows(Array.isArray(away) ? away : []);
  }, []);

  const loadAll = useCallback(async () => {
    try {
      setLoadError("");
      const matches = await loadLiveMatches();
      const currentId = selectedMatchIdRef.current;
      const target = matches.find((m) => m.id === currentId) || matches[0] || null;
      await loadHistories(target);
      setLastUpdate(formatClock(new Date()));
    } catch {
      setLoadError("Não foi possível conectar ao backend. Verifique se o servidor FastAPI está rodando.");
    }
  }, [loadLiveMatches, loadHistories]);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadHistories(selectedMatch);
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

  const leagueApiId = selectedMatch?.league?.api_id ?? null;
  const homeStats = useMemo(
    () =>
      computeStats(homeRows, { gamesCount, sameVenue, venueIsHome: true, sameCompetition, leagueApiId }),
    [homeRows, gamesCount, sameVenue, sameCompetition, leagueApiId]
  );
  const awayStats = useMemo(
    () =>
      computeStats(awayRows, { gamesCount, sameVenue, venueIsHome: false, sameCompetition, leagueApiId }),
    [awayRows, gamesCount, sameVenue, sameCompetition, leagueApiId]
  );

  const showHt = homeStats.htN > 0 && awayStats.htN > 0;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <Header
        lastUpdate={lastUpdate}
        onRefresh={handleRefresh}
        refreshing={refreshing}
        onOpenSidebar={onOpenSidebar}
        title="COMPARATIVO HISTÓRICO"
        subtitle="Forma recente dos dois times - resultados, gols e over/under nos últimos jogos"
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
          <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
            <div className="flex items-center justify-between text-sm font-medium px-1 mb-4">
              <span className="text-blue-400 truncate">{selectedMatch.home_team.name}</span>
              <span className="text-slate-400 text-xs">forma recente</span>
              <span className="text-red-400 truncate">{selectedMatch.away_team.name}</span>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-3 mb-5 pb-5 border-b border-border">
              <label className="flex items-center gap-2 text-xs text-slate-300">
                Jogos:
                <input
                  type="range"
                  min={MIN_GAMES}
                  max={MAX_GAMES}
                  value={gamesCount}
                  onChange={(e) => setGamesCount(Number(e.target.value))}
                  className="w-32 accent-accent"
                />
                <span className="w-6 text-center font-semibold text-slate-100">{gamesCount}</span>
              </label>
              <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={sameVenue}
                  onChange={(e) => setSameVenue(e.target.checked)}
                  className="accent-accent"
                />
                Mesmo Mando
              </label>
              <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={sameCompetition}
                  onChange={(e) => setSameCompetition(e.target.checked)}
                  className="accent-accent"
                />
                Na Competição
              </label>
            </div>

            <p className="text-center text-[11px] text-muted mb-4">
              Baseado em {homeStats.n} jogo{homeStats.n === 1 ? "" : "s"} de{" "}
              <span className="text-blue-400">{selectedMatch.home_team.name}</span> e {awayStats.n} jogo
              {awayStats.n === 1 ? "" : "s"} de <span className="text-red-400">{selectedMatch.away_team.name}</span>
              {sameVenue ? " (mesmo mando de campo)" : ""}
              {sameCompetition ? " (só nesta competição)" : ""}
              {(homeStats.n < gamesCount || awayStats.n < gamesCount)
                ? " - algum dos dois times ainda não tem jogos suficientes para o filtro pedido"
                : ""}
            </p>

            <div className="space-y-6">
              <Section title="Resultados">
                <StatRow label="Vitórias" home={homeStats.wins} away={awayStats.wins} />
                <StatRow label="Empates" home={homeStats.draws} away={awayStats.draws} />
                <StatRow label="Derrotas" home={homeStats.losses} away={awayStats.losses} />
              </Section>

              <Section title="Gols por Jogo (média)">
                <StatRow label="Gols Marcados" home={homeStats.avgGoalsFor} away={awayStats.avgGoalsFor} />
                <StatRow label="Gols Sofridos" home={homeStats.avgGoalsAgainst} away={awayStats.avgGoalsAgainst} />
              </Section>

              <Section title="Over/Under Gols" note="quantidade de jogos, não %">
                {OU_LINES.map((line) => (
                  <StatRow
                    key={line}
                    label={`Mais de ${line}`}
                    home={homeStats.overCounts[line]}
                    away={awayStats.overCounts[line]}
                  />
                ))}
                <StatRow label="Ambas Marcam" home={homeStats.btts} away={awayStats.btts} />
              </Section>

              {showHt ? (
                <Section
                  title="1º Tempo"
                  note={`baseado em ${homeStats.htN}/${awayStats.htN} jogos com placar de intervalo disponível`}
                >
                  <StatRow label="Vitórias HT" home={homeStats.htWins} away={awayStats.htWins} />
                  <StatRow label="Empates HT" home={homeStats.htDraws} away={awayStats.htDraws} />
                  <StatRow label="Derrotas HT" home={homeStats.htLosses} away={awayStats.htLosses} />
                  <StatRow
                    label="Gols Marcados HT"
                    home={homeStats.avgHtGoalsFor}
                    away={awayStats.avgHtGoalsFor}
                  />
                  {OU_LINES.map((line) => (
                    <StatRow
                      key={`ht-${line}`}
                      label={`Mais de ${line} HT`}
                      home={homeStats.htOverCounts[line]}
                      away={awayStats.htOverCounts[line]}
                    />
                  ))}
                  <StatRow label="Ambas Marcam HT" home={homeStats.htBtts} away={awayStats.htBtts} />
                </Section>
              ) : (
                <p className="text-center text-xs text-muted">
                  Placar do intervalo indisponível para jogos suficientes de um dos dois times - seção "1º Tempo"
                  omitida em vez de mostrar dado incompleto.
                </p>
              )}
            </div>

            <p className="text-center text-[10px] text-muted mt-6 pt-4 border-t border-border">
              Odds mínima/média/máxima de cada jogo passado ainda não estão disponíveis nesta tela - dependem de
              buscar as odds pré-jogo de cada partida do histórico, o que tem custo de API por jogo e cobertura
              que pode variar por liga.
            </p>
          </div>
        ) : (
          <div className="bg-panel border border-border rounded-xl p-10 text-center">
            <p className="text-slate-200 font-medium mb-1">Nenhuma partida ao vivo monitorada no momento</p>
            <p className="text-sm text-muted">
              Assim que uma partida entrar em observação, o comparativo histórico dos dois times aparece aqui.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
