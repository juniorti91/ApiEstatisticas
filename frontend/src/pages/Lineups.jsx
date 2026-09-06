import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ShieldAlert, Users } from "lucide-react";
import { ApiClient } from "../api/client";
import Header from "../components/Header";
import LiveMatchCard from "../components/LiveMatchCard";

const POLL_MS = 60000; // escalação/árbitro/lesões não mudam durante o jogo - poll bem mais espaçado que as outras telas

function formatClock(date) {
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// "linha:posicao" (ex: "2:3") -> {line, pos}. None/formato invalido ->
// null, pra cair no fallback "sem posição definida" em vez de desenhar
// errado em cima do campo.
function parseGrid(grid) {
  if (!grid || typeof grid !== "string") return null;
  const parts = grid.split(":");
  if (parts.length !== 2) return null;
  const line = Number(parts[0]);
  const pos = Number(parts[1]);
  if (!Number.isFinite(line) || !Number.isFinite(pos)) return null;
  return { line, pos };
}

// Distribui os jogadores num campo horizontal: colunas = linhas taticas
// (goleiro, zaga, meio, ataque...), esquerda->direita pro time da casa e
// espelhado (direita->esquerda) pro visitante - mesma leitura da
// referência (os dois goleiros ficam encostados nas bordas do campo, os
// atacantes perto do meio-campo).
function layoutPlayers(players, isHome) {
  const withGrid = [];
  const withoutGrid = [];
  for (const p of players) {
    const g = parseGrid(p.grid);
    if (g) withGrid.push({ ...p, ...g });
    else withoutGrid.push(p);
  }
  if (withGrid.length === 0) return { placed: [], unplaced: players };

  const lines = Array.from(new Set(withGrid.map((p) => p.line))).sort((a, b) => a - b);
  const maxLine = lines.length;

  const placed = withGrid.map((p) => {
    const colIndex = lines.indexOf(p.line); // 0 = goleiro
    const sameLine = withGrid.filter((q) => q.line === p.line).sort((a, b) => a.pos - b.pos);
    const rowIndex = sameLine.findIndex((q) => q === p || (q.name === p.name && q.pos === p.pos));
    const rowCount = sameLine.length;

    // Margem de 8% pra nao colar o goleiro na borda nem o ultimo atacante
    // muito perto do meio-campo.
    const xWithinHalf = maxLine > 1 ? (colIndex / (maxLine - 1)) * 37 + 8 : 8;
    const xPct = isHome ? xWithinHalf : 100 - xWithinHalf;
    const yPct = ((rowIndex + 1) / (rowCount + 1)) * 100;

    return { ...p, xPct, yPct };
  });

  return { placed, unplaced: withoutGrid };
}

function PlayerChip({ player, colorClass, borderClass }) {
  return (
    <div
      className="absolute flex flex-col items-center gap-0.5 -translate-x-1/2 -translate-y-1/2 w-14 sm:w-16"
      style={{ left: `${player.xPct}%`, top: `${player.yPct}%` }}
    >
      <div
        className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-[11px] sm:text-xs font-bold border-2 bg-panel ${colorClass} ${borderClass}`}
      >
        {player.number ?? "?"}
      </div>
      <span className="text-[9px] sm:text-[10px] text-slate-200 text-center leading-tight truncate w-full">
        {player.name}
      </span>
    </div>
  );
}

function Pitch({ homePlayers, awayPlayers }) {
  const home = layoutPlayers(homePlayers, true);
  const away = layoutPlayers(awayPlayers, false);

  return (
    <div>
      <div className="relative w-full aspect-[16/9] bg-[#0d2818] border border-border rounded-lg overflow-hidden">
        {/* Marcações do campo - so decorativas, em branco translucido pra combinar com o tema escuro */}
        <div className="absolute inset-0 border-2 border-white/15 m-2 sm:m-3 rounded-sm" />
        <div className="absolute top-2 sm:top-3 bottom-2 sm:bottom-3 left-1/2 w-px bg-white/15" />
        <div className="absolute top-1/2 left-1/2 w-16 h-16 sm:w-24 sm:h-24 -translate-x-1/2 -translate-y-1/2 border-2 border-white/15 rounded-full" />
        <div className="absolute top-1/2 left-2 sm:left-3 w-8 h-20 sm:w-12 sm:h-28 -translate-y-1/2 border-2 border-l-0 border-white/15" />
        <div className="absolute top-1/2 right-2 sm:right-3 w-8 h-20 sm:w-12 sm:h-28 -translate-y-1/2 border-2 border-r-0 border-white/15" />

        {home.placed.map((p, i) => (
          <PlayerChip key={`h-${i}`} player={p} colorClass="text-blue-400" borderClass="border-blue-500" />
        ))}
        {away.placed.map((p, i) => (
          <PlayerChip key={`a-${i}`} player={p} colorClass="text-red-400" borderClass="border-red-500" />
        ))}
      </div>

      {(home.unplaced.length > 0 || away.unplaced.length > 0) && (
        <div className="grid grid-cols-2 gap-3 mt-3 text-xs">
          {home.unplaced.length > 0 && (
            <div className="text-blue-400">
              {home.unplaced.map((p, i) => (
                <div key={i} className="text-slate-300">
                  <span className="text-blue-400">{p.number ?? "?"}</span> {p.name}
                </div>
              ))}
            </div>
          )}
          {away.unplaced.length > 0 && (
            <div className="text-right">
              {away.unplaced.map((p, i) => (
                <div key={i} className="text-slate-300">
                  {p.name} <span className="text-red-400">{p.number ?? "?"}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SubstitutesList({ homeSubs, awaySubs }) {
  if (homeSubs.length === 0 && awaySubs.length === 0) return null;
  const max = Math.max(homeSubs.length, awaySubs.length);
  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="text-xs font-semibold text-muted tracking-wide mb-3">BANCO DE RESERVAS</div>
      <div className="grid grid-cols-2 gap-x-4 text-sm">
        <div className="space-y-1.5">
          {homeSubs.map((p, i) => (
            <div key={i} className="text-slate-300">
              <span className="text-blue-400 w-6 inline-block">{p.number ?? "?"}</span> {p.name}
            </div>
          ))}
        </div>
        <div className="space-y-1.5 text-right">
          {awaySubs.map((p, i) => (
            <div key={i} className="text-slate-300">
              {p.name} <span className="text-red-400 w-6 inline-block">{p.number ?? "?"}</span>
            </div>
          ))}
        </div>
      </div>
      {max === 0 && <p className="text-xs text-muted">Nenhum reserva informado.</p>}
    </div>
  );
}

function InjuriesList({ homeName, awayName, homeInjuries, awayInjuries }) {
  if (homeInjuries.length === 0 && awayInjuries.length === 0) return null;
  return (
    <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
      <div className="flex items-center gap-2 text-xs font-semibold text-muted tracking-wide mb-3">
        <ShieldAlert size={14} /> LESÕES E SUSPENSÕES
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <div className="text-xs text-blue-400 font-medium mb-2 truncate">{homeName}</div>
          <div className="space-y-2">
            {homeInjuries.map((inj, i) => (
              <div key={i} className="text-sm text-slate-300">
                {inj.player_name}
                <span className="block text-xs text-red-400">{inj.reason}</span>
              </div>
            ))}
            {homeInjuries.length === 0 && <p className="text-xs text-muted">Nenhuma informada.</p>}
          </div>
        </div>
        <div>
          <div className="text-xs text-red-400 font-medium mb-2 truncate">{awayName}</div>
          <div className="space-y-2">
            {awayInjuries.map((inj, i) => (
              <div key={i} className="text-sm text-slate-300">
                {inj.player_name}
                <span className="block text-xs text-red-400">{inj.reason}</span>
              </div>
            ))}
            {awayInjuries.length === 0 && <p className="text-xs text-muted">Nenhuma informada.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Lineups({ selectedLeague, onLeaguesChange, onOpenSidebar }) {
  const [liveMatches, setLiveMatches] = useState([]);
  const [selectedMatchId, setSelectedMatchId] = useState(null);
  const [lineup, setLineup] = useState(null);
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

  const loadLineup = useCallback(async (matchId) => {
    if (!matchId) {
      setLineup(null);
      return;
    }
    const data = await ApiClient.getLineups(matchId).catch(() => null);
    setLineup(data);
  }, []);

  const loadAll = useCallback(async () => {
    try {
      setLoadError("");
      const matches = await loadLiveMatches();
      const currentId = selectedMatchIdRef.current;
      const targetId = matches.some((m) => m.id === currentId) ? currentId : matches[0]?.id ?? null;
      await loadLineup(targetId);
      setLastUpdate(formatClock(new Date()));
    } catch {
      setLoadError("Não foi possível conectar ao backend. Verifique se o servidor FastAPI está rodando.");
    }
  }, [loadLiveMatches, loadLineup]);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadLineup(selectedMatchId);
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
        possessionHome: 50,
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
        title="ESCALAÇÕES"
        subtitle="Prováveis titulares, técnicos, árbitro e lesões/suspensões"
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

            {!lineup?.lineup_available && (
              <div className="bg-panel border border-border rounded-xl p-6 text-center">
                <Users size={22} className="text-muted mx-auto mb-2" />
                <p className="text-slate-200 font-medium mb-1">Escalação ainda não publicada</p>
                <p className="text-sm text-muted">
                  A API costuma divulgar a escalação titular cerca de 1h antes do apito inicial - tentando de
                  novo automaticamente.
                  {lineup?.referee ? ` Árbitro já confirmado: ${lineup.referee}.` : ""}
                </p>
              </div>
            )}

            {lineup?.lineup_available && (
              <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
                <div className="flex items-center justify-between text-sm font-medium px-1 mb-4">
                  <span className="text-blue-400 truncate">
                    {selectedMatch.home_team.name} {lineup.formation_home ? `(${lineup.formation_home})` : ""}
                  </span>
                  <span className="text-red-400 truncate">
                    {lineup.formation_away ? `(${lineup.formation_away})` : ""} {selectedMatch.away_team.name}
                  </span>
                </div>
                <Pitch homePlayers={lineup.lineup_home} awayPlayers={lineup.lineup_away} />
              </div>
            )}

            {lineup?.lineup_available && (
              <SubstitutesList homeSubs={lineup.substitutes_home} awaySubs={lineup.substitutes_away} />
            )}

            {(lineup?.coach_home || lineup?.coach_away || lineup?.referee) && (
              <div className="bg-panel border border-border rounded-xl p-4 sm:p-5">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-xs text-muted mb-1">TÉCNICO - {selectedMatch.home_team.name}</div>
                    <div className="text-sm text-slate-200">{lineup.coach_home || "Não informado"}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted mb-1">ÁRBITRO</div>
                    <div className="text-sm text-slate-200">{lineup.referee || "Não informado"}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted mb-1">TÉCNICO - {selectedMatch.away_team.name}</div>
                    <div className="text-sm text-slate-200">{lineup.coach_away || "Não informado"}</div>
                  </div>
                </div>
              </div>
            )}

            {lineup && (
              <InjuriesList
                homeName={selectedMatch.home_team.name}
                awayName={selectedMatch.away_team.name}
                homeInjuries={lineup.injuries_home}
                awayInjuries={lineup.injuries_away}
              />
            )}
          </>
        ) : (
          <div className="bg-panel border border-border rounded-xl p-10 text-center">
            <p className="text-slate-200 font-medium mb-1">Nenhuma partida ao vivo monitorada no momento</p>
            <p className="text-sm text-muted">
              Assim que uma partida entrar em observação, a escalação aparece aqui quando publicada pela API.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
