import { useCallback, useState } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import LiveMatches from "./pages/LiveMatches";
import MatchData from "./pages/MatchData";
import MatchStats from "./pages/MatchStats";

export default function App() {
  // Pagina atual - navegacao simples por estado (sem router: o app so tem
  // poucas telas reais por enquanto, uma lib de rotas seria exagero aqui).
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [selectedLeague, setSelectedLeague] = useState("Todas");
  const [onlyValueBets, setOnlyValueBets] = useState(false);
  // Ligas disponíveis no dashboard agora vêm das partidas ao vivo realmente
  // retornadas pelo backend (Dashboard informa a lista via onLeaguesChange),
  // em vez de uma lista fixa que podia não bater com o que está em jogo.
  const [leagues, setLeagues] = useState([]);
  // Em telas pequenas a barra lateral vira uma gaveta (drawer) escondida por
  // padrão, aberta pelo botão de menu no cabeçalho - em telas médias/grandes
  // (md:) ela fica sempre visível, fixa, como antes.
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLeaguesChange = useCallback((newLeagues) => {
    setLeagues((prev) => {
      const same =
        prev.length === newLeagues.length && prev.every((l, i) => l === newLeagues[i]);
      return same ? prev : newLeagues;
    });
    // Se a liga selecionada deixou de existir entre as partidas ao vivo
    // (ex.: a partida acabou), volta o filtro para "Todas" em vez de deixar
    // a lista vazia silenciosamente.
    setSelectedLeague((prevSelected) =>
      prevSelected === "Todas" || newLeagues.includes(prevSelected) ? prevSelected : "Todas"
    );
  }, []);

  return (
    <div className="flex h-screen bg-base overflow-hidden">
      <Sidebar
        leagues={leagues}
        selectedLeague={selectedLeague}
        onLeagueChange={(league) => {
          setSelectedLeague(league);
          setSidebarOpen(false);
        }}
        onlyValueBets={onlyValueBets}
        onToggleValueBets={() => setOnlyValueBets((v) => !v)}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        currentPage={currentPage}
        onNavigate={setCurrentPage}
      />
      {currentPage === "live" ? (
        <LiveMatches
          selectedLeague={selectedLeague}
          onLeaguesChange={handleLeaguesChange}
          onOpenSidebar={() => setSidebarOpen(true)}
        />
      ) : currentPage === "matchdata" ? (
        <MatchData
          selectedLeague={selectedLeague}
          onLeaguesChange={handleLeaguesChange}
          onOpenSidebar={() => setSidebarOpen(true)}
        />
      ) : currentPage === "matchstats" ? (
        <MatchStats
          selectedLeague={selectedLeague}
          onLeaguesChange={handleLeaguesChange}
          onOpenSidebar={() => setSidebarOpen(true)}
        />
      ) : (
        <Dashboard
          onlyValueBets={onlyValueBets}
          selectedLeague={selectedLeague}
          onLeaguesChange={handleLeaguesChange}
          onOpenSidebar={() => setSidebarOpen(true)}
        />
      )}
    </div>
  );
}
