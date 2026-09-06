import { useCallback, useEffect, useState } from "react";
import { ApiClient } from "../api/client";
import Header from "../components/Header";
import RecommendationHistoryTable from "../components/RecommendationHistoryTable";

const POLL_MS = 15000;
// Teto maximo aceito pelo backend (GET /api/history/recommendations, query
// `limit` com le=200 - ver app/routers/history.py) - diferente do resumo
// mostrado no card do Dashboard (que so busca as ultimas 50), esta e a
// pagina dedicada "ver todas", entao busca o maximo permitido de uma vez.
const HISTORY_LIMIT = 200;

function formatClock(date) {
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// Pagina dedicada ao historico de recomendacoes - antes essa tabela so
// existia dentro do Dashboard e, pior, só aparecia quando havia uma
// partida ao vivo selecionada (ficava escondida sem nenhum jogo em
// andamento). Aqui ela fica visivel sempre, com o historico completo (ate
// 200 linhas) em vez do recorte de 50 do resumo do Dashboard.
export default function Recommendations({ onOpenSidebar }) {
  const [history, setHistory] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(formatClock(new Date()));
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState("");

  const loadAll = useCallback(async () => {
    try {
      setLoadError("");
      const hist = await ApiClient.getHistory(HISTORY_LIMIT);
      setHistory(Array.isArray(hist) ? hist : []);
      setLastUpdate(formatClock(new Date()));
    } catch {
      setLoadError("Não foi possível conectar ao backend. Verifique se o servidor FastAPI está rodando.");
    }
  }, []);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await loadAll();
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <Header
        lastUpdate={lastUpdate}
        onRefresh={handleRefresh}
        refreshing={refreshing}
        onOpenSidebar={onOpenSidebar}
        title="RECOMENDAÇÕES"
        subtitle="Histórico completo das recomendações geradas, com odd, resultado e acerto"
      />

      <div className="flex-1 overflow-y-auto overflow-x-hidden px-4 sm:px-6 py-4 sm:py-5 space-y-5">
        {loadError && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-300 text-sm rounded-lg px-4 py-3">
            {loadError}
          </div>
        )}

        <RecommendationHistoryTable rows={history} />
      </div>
    </div>
  );
}
