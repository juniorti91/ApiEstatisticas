import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiClient } from "../api/client";
import Header from "../components/Header";
import LiveMatchCard from "../components/LiveMatchCard";
import StatsComparisonPanel from "../components/StatsComparisonPanel";
import PerformanceComparisonTable from "../components/PerformanceComparisonTable";
import MatchInfoCard from "../components/MatchInfoCard";
import MomentumTimeline from "../components/MomentumTimeline";
import MatchReport from "../components/MatchReport";
import EvolutionChart from "../components/EvolutionChart";
import OddsMovementChart from "../components/OddsMovementChart";
import MainRecommendationCard from "../components/MainRecommendationCard";
import OtherRecommendations from "../components/OtherRecommendations";
import RecommendationHistoryTable from "../components/RecommendationHistoryTable";
import PerformanceFooter from "../components/PerformanceFooter";
import ManualEntryPanel from "../components/ManualEntryPanel";

// Intervalo de atualização da TELA (le do banco local via nosso backend -
// nao consome cota da API-Football, so consulta o que ja foi coletado).
// Reduzido de 30s para 12s para o dashboard parecer mais "vivo"; isso NAO
// aumenta o numero de chamadas feitas ao api-football.com, que continuam
// controladas apenas pelo agendador do backend (varredura a cada 2 min,
// coleta de estatisticas a cada 5 min - ver COLLECTOR_INTERVAL_MINUTES).
const POLL_MS = 12000;

function formatClock(date) {
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function Dashboard({ onlyValueBets, selectedLeague, onLeaguesChange, onOpenSidebar }) {
  const [liveMatches, setLiveMatches] = useState([]);
  const [selectedMatchId, setSelectedMatchId] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [events, setEvents] = useState([]);
  // Serie do Indice de Momentum ao longo do jogo (ver prognostics_service.
  // compute_momentum_series) - alimenta o mini-grafico "Fluxo da partida"
  // embutido no card do placar (LiveMatchCard), visivel em todas as abas.
  const [flowSeries, setFlowSeries] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [oddsHistory, setOddsHistory] = useState([]);
  const [history, setHistory] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [activeTab, setActiveTab] = useState("Visão Geral");
  const [lastUpdate, setLastUpdate] = useState(formatClock(new Date()));
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState("");

  // Guarda o id da partida selecionada também num ref, para que o
  // auto-refresh periódico (useEffect com [] logo abaixo) sempre leia o
  // valor MAIS RECENTE. Sem isso, cada "tick" do timer usa a closure
  // "congelada" no momento em que o app montou (selectedMatchId = null
  // nesse instante) e força a seleção de volta pra primeira partida da
  // lista a cada atualização automática - desfazendo o clique do usuário
  // num outro jogo, ou a partida escolhida pelo filtro de liga, poucos
  // segundos depois.
  const selectedMatchIdRef = useRef(selectedMatchId);
  useEffect(() => {
    selectedMatchIdRef.current = selectedMatchId;
  }, [selectedMatchId]);

  // Partidas realmente visíveis após o filtro de liga escolhido na barra
  // lateral. A partida selecionada e exibida no painel principal precisa
  // vir DESSA lista (não de liveMatches inteira), senão o filtro só afeta
  // a fileira de abas e o painel continua mostrando um jogo de outra liga.
  const filteredMatches = useMemo(
    () => liveMatches.filter((m) => selectedLeague === "Todas" || m.league?.name === selectedLeague),
    [liveMatches, selectedLeague]
  );

  const selectedMatch = useMemo(() => {
    const found = filteredMatches.find((m) => m.id === selectedMatchId) || null;
    // eslint-disable-next-line no-console
    console.log(
      "[BetAnalyzer][selectedMatch recalculado] selectedMatchId:", selectedMatchId,
      "| encontrado:", found ? `${found.home_team.name} x ${found.away_team.name} (id ${found.id})` : "NENHUM"
    );
    return found;
  }, [filteredMatches, selectedMatchId]);

  // Sempre que a liga filtrada mudar (ou a partida selecionada sair do
  // filtro por qualquer motivo), troca automaticamente para a primeira
  // partida que pertence à liga selecionada.
  useEffect(() => {
    if (!filteredMatches.some((m) => m.id === selectedMatchId)) {
      // eslint-disable-next-line no-console
      console.warn(
        "[BetAnalyzer][filteredMatches-effect] RESET: id", selectedMatchId,
        "nao encontrado na lista filtrada", filteredMatches.map((m) => m.id),
        "- trocando para", filteredMatches[0]?.id ?? null
      );
      setSelectedMatchId(filteredMatches[0]?.id ?? null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filteredMatches]);

  const loadLiveMatches = useCallback(async () => {
    const raw = await ApiClient.listLiveMatches();
    // Blindagem: se a API (ou um proxy/servidor mal configurado no caminho)
    // devolver algo que nao seja uma lista, nunca deixa isso quebrar a tela
    // inteira - so trata como "nenhuma partida" em vez de dar erro de
    // renderizacao (ja aconteceu em teste: um servidor estatico respondendo
    // HTML no lugar do JSON esperado travava o app inteiro com tela branca).
    const matches = Array.isArray(raw) ? raw : [];
    setLiveMatches(matches);
    const currentId = selectedMatchIdRef.current;
    // eslint-disable-next-line no-console
    console.log(
      "[BetAnalyzer][loadLiveMatches] ids recebidos:", matches.map((m) => m.id),
      "| selecionado atualmente (ref):", currentId
    );
    if (matches.length > 0 && !matches.some((m) => m.id === currentId)) {
      // eslint-disable-next-line no-console
      console.warn(
        "[BetAnalyzer][loadLiveMatches] RESET: id", currentId,
        "nao encontrado na lista completa - trocando para", matches[0].id
      );
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

  const loadMatchDetail = useCallback(async (matchId) => {
    if (!matchId) {
      setSnapshots([]);
      setComparison(null);
      setEvents([]);
      setFlowSeries([]);
      setRecommendations([]);
      setOddsHistory([]);
      return;
    }
    const [rawSnaps, rawComp, rawEvents, rawRecs, rawPrognostics] = await Promise.all([
      ApiClient.getSnapshots(matchId).catch(() => []),
      ApiClient.getComparison(matchId).catch(() => null),
      // Eventos tem cache curto (60s) so enquanto a partida esta ao vivo -
      // ver app/services/events_service.py - por isso e seguro buscar
      // junto do resto a cada ciclo normal de atualizacao da tela (12s),
      // sem gerar chamada nova a API-Football a cada poll.
      ApiClient.getEvents(matchId).catch(() => ({ events: [] })),
      ApiClient.listFixtureRecommendations(matchId).catch(() => []),
      // Prognosticos e so leitura dos snapshots ja salvos (nenhuma chamada
      // nova a API-Football) - buscado aqui so pela momentum_series, que
      // alimenta o mini-grafico "Fluxo da partida" no card do placar.
      ApiClient.getPrognostics(matchId).catch(() => null),
    ]);
    const snaps = Array.isArray(rawSnaps) ? rawSnaps : [];
    const recs = Array.isArray(rawRecs) ? rawRecs : [];
    setSnapshots(snaps);
    setComparison(rawComp);
    setEvents(Array.isArray(rawEvents?.events) ? rawEvents.events : []);
    setFlowSeries(Array.isArray(rawPrognostics?.momentum_series) ? rawPrognostics.momentum_series : []);
    setRecommendations(recs);

    const primary = recs.find((r) => r.is_primary) || recs[0];
    if (primary) {
      const rawHist = await ApiClient.getOddsHistory(primary.id).catch(() => []);
      setOddsHistory(Array.isArray(rawHist) ? rawHist : []);
    } else {
      setOddsHistory([]);
    }
  }, []);

  const loadAncillary = useCallback(async () => {
    const [hist, perf] = await Promise.all([
      ApiClient.getHistory(50).catch(() => []),
      ApiClient.getPerformance(30).catch(() => null),
    ]);
    setHistory(Array.isArray(hist) ? hist : []);
    setPerformance(perf);
  }, []);

  const loadAll = useCallback(async () => {
    try {
      setLoadError("");
      const matches = await loadLiveMatches();
      const currentId = selectedMatchIdRef.current;
      const targetId = matches.some((m) => m.id === currentId) ? currentId : matches[0]?.id ?? null;
      await Promise.all([loadMatchDetail(targetId), loadAncillary()]);
      setLastUpdate(formatClock(new Date()));
    } catch (err) {
      setLoadError("Não foi possível conectar ao backend. Verifique se o servidor FastAPI está rodando.");
    }
  }, [loadLiveMatches, loadMatchDetail, loadAncillary]);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadMatchDetail(selectedMatchId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMatchId]);

  // O botao ATUALIZAR nao dispara mais um ciclo completo de coleta (isso
  // continua so automatico, a cada 5 min - ver COLLECTOR_INTERVAL_MINUTES)
  // pra nao gastar chamadas de estatisticas a cada clique. Mas ele FORCA
  // na hora o ciclo de odds/recomendacoes (o mesmo que ja roda sozinho a
  // cada ODDS_REFRESH_INTERVAL_MINUTES) antes de reler o banco, pra toda
  // odd exibida na tela vir recem-calculada em vez de mostrar o que ja
  // estava salvo ha ate alguns minutos.
  async function handleRefresh() {
    setRefreshing(true);
    try {
      await ApiClient.refreshOdds().catch(() => null);
      await loadAll();
    } catch {
      setLoadError("Falha ao atualizar - o backend pode estar offline.");
    } finally {
      setRefreshing(false);
    }
  }

  // Uso ocasional: forca uma nova coleta ao vivo na API-Football agora
  // mesmo (gasta requisicoes de verdade). Reservado para quando o usuario
  // acabou de monitorar uma partida manualmente e nao quer esperar o
  // proximo ciclo automatico.
  async function handleForceCollect() {
    setRefreshing(true);
    try {
      await ApiClient.collectNow();
      await loadAll();
    } catch {
      setLoadError("Falha ao disparar coleta manual - o backend pode estar offline.");
    } finally {
      setRefreshing(false);
    }
  }

  const latestSnapshot = snapshots.length ? snapshots[snapshots.length - 1] : null;
  const filteredRecommendations = onlyValueBets
    ? recommendations.filter((r) => r.is_value_bet)
    : recommendations;
  const primaryRec = filteredRecommendations.find((r) => r.is_primary) || filteredRecommendations[0];
  const otherRecs = filteredRecommendations.filter((r) => r.id !== primaryRec?.id);

  const matchForCard = selectedMatch
    ? {
        ...selectedMatch,
        possessionHome: latestSnapshot ? Math.round(latestSnapshot.possession_home) : 50,
        periodLabel: selectedMatch.status === "HT" ? "Intervalo" : selectedMatch.status === "2H" ? "2º TEMPO" : "1º TEMPO",
      }
    : null;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <Header lastUpdate={lastUpdate} onRefresh={handleRefresh} refreshing={refreshing} onOpenSidebar={onOpenSidebar} />

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
                onClick={() => {
                  // eslint-disable-next-line no-console
                  console.log("[BetAnalyzer][clique do usuario] selecionando partida id", m.id);
                  setSelectedMatchId(m.id);
                }}
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
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div className="lg:col-span-2 space-y-5 min-w-0">
              <LiveMatchCard
                match={matchForCard}
                activeTab={activeTab}
                onTabChange={setActiveTab}
                showFlow
                flowSeries={flowSeries}
              />

              {activeTab === "Visão Geral" && (
                <div className="space-y-5">
                  <MatchInfoCard matchId={selectedMatch.id} match={selectedMatch} />
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    <StatsComparisonPanel
                      homeName={selectedMatch.home_team.name}
                      awayName={selectedMatch.away_team.name}
                      snapshot={latestSnapshot}
                    />
                    <PerformanceComparisonTable
                      comparison={comparison}
                      elapsedMinutes={selectedMatch.elapsed_minutes}
                      homeName={selectedMatch.home_team.name}
                      awayName={selectedMatch.away_team.name}
                    />
                  </div>
                </div>
              )}

              {activeTab === "Eventos" && (
                <MomentumTimeline
                  events={events}
                  homeName={selectedMatch.home_team.name}
                  awayName={selectedMatch.away_team.name}
                />
              )}

              {activeTab === "Relato" && (
                <MatchReport
                  events={events}
                  homeName={selectedMatch.home_team.name}
                  awayName={selectedMatch.away_team.name}
                />
              )}

              {activeTab === "Comparativo" && (
                <PerformanceComparisonTable
                  comparison={comparison}
                  elapsedMinutes={selectedMatch.elapsed_minutes}
                  homeName={selectedMatch.home_team.name}
                  awayName={selectedMatch.away_team.name}
                />
              )}

              {activeTab === "Estatísticas" && (
                <StatsComparisonPanel
                  homeName={selectedMatch.home_team.name}
                  awayName={selectedMatch.away_team.name}
                  snapshot={latestSnapshot}
                />
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <EvolutionChart
                  snapshots={snapshots}
                  homeName={selectedMatch.home_team.name}
                  awayName={selectedMatch.away_team.name}
                />
                <OddsMovementChart history={oddsHistory} marketLabel={primaryRec?.selection} />
              </div>

              <RecommendationHistoryTable rows={history} />
            </div>

            <div className="space-y-5">
              <MainRecommendationCard recommendation={primaryRec} />
              <OtherRecommendations recommendations={otherRecs} allRecommendations={filteredRecommendations} />
              <ManualEntryPanel
                selectedMatch={selectedMatch}
                onTracked={handleForceCollect}
                onSnapshotAdded={() => loadMatchDetail(selectedMatchId)}
              />
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div className="lg:col-span-2 bg-panel border border-border rounded-xl p-10 text-center">
              {liveMatches.length > 0 && selectedLeague !== "Todas" ? (
                <>
                  <p className="text-slate-200 font-medium mb-1">
                    Nenhuma partida ao vivo na liga "{selectedLeague}" no momento
                  </p>
                  <p className="text-sm text-muted">
                    Há {liveMatches.length} partida(s) ao vivo em outras ligas. Selecione "Todas" no filtro de
                    ligas na barra lateral para vê-las.
                  </p>
                </>
              ) : (
                <>
                  <p className="text-slate-200 font-medium mb-1">Nenhuma partida ao vivo monitorada no momento</p>
                  <p className="text-sm text-muted">
                    O sistema varre automaticamente as ligas configuradas a cada 2 minutos. Você também pode
                    monitorar uma partida específica manualmente ao lado, informando o ID dela na API-Football.
                  </p>
                </>
              )}
            </div>
            <ManualEntryPanel selectedMatch={null} onTracked={handleForceCollect} />
          </div>
        )}

        <PerformanceFooter performance={performance} />
      </div>
    </div>
  );
}
