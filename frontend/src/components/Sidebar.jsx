import {
  LayoutDashboard,
  Radio,
  Database,
  BarChart3,
  Zap,
  ClipboardList,
  LineChart,
  Users,
  Settings,
  Crown,
  X,
} from "lucide-react";

// Paginas de verdade, navegaveis (ver App.jsx). As demais entradas ainda
// nao tem tela propria - ficam visiveis (proximos passos do produto) mas
// sem acao ao clicar, em vez de sumir da barra lateral.
const NAV_ITEMS = [
  { label: "Dashboard", icon: LayoutDashboard, page: "dashboard" },
  { label: "Partidas Ao Vivo", icon: Radio, page: "live" },
  { label: "Dados do Jogo", icon: Database, page: "matchdata" },
  { label: "Comparativo Detalhado", icon: BarChart3, page: "matchstats" },
  { label: "Recomendações", icon: Zap },
  { label: "Histórico de Apostas", icon: ClipboardList },
  { label: "Análises", icon: LineChart },
  { label: "Times", icon: Users },
  { label: "Configurações", icon: Settings },
];

export default function Sidebar({
  leagues,
  selectedLeague,
  onLeagueChange,
  onlyValueBets,
  onToggleValueBets,
  open,
  onClose,
  currentPage,
  onNavigate,
}) {
  return (
    <>
      {/* Fundo escurecido atras da gaveta, so no mobile e so quando aberta -
          clicar nele fecha a barra lateral. Nao existe (nem recebe cliques)
          em telas md+ onde a barra ja fica sempre visivel e fixa. */}
      {open && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 shrink-0 bg-panel border-r border-border flex flex-col h-full
        transform transition-transform duration-200 ease-in-out
        ${open ? "translate-x-0" : "-translate-x-full"} md:translate-x-0 md:static md:z-auto`}
      >
        <div className="px-5 py-5 flex items-center justify-between gap-2 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg bg-accentdim flex items-center justify-center">
              <LineChart size={18} className="text-accent" />
            </div>
            <div>
              <div className="font-semibold text-slate-100 leading-tight">BetAnalyzer</div>
              <div className="text-[10px] tracking-widest text-muted">IN-PLAY ANALYTICS</div>
            </div>
          </div>
          <button onClick={onClose} className="text-muted hover:text-slate-200 md:hidden" aria-label="Fechar menu">
            <X size={20} />
          </button>
        </div>

      <nav className="flex-1 py-4 px-3 space-y-1">
        {NAV_ITEMS.map(({ label, icon: Icon, page }) => {
          const active = page && page === currentPage;
          return (
            <button
              key={label}
              disabled={!page}
              onClick={() => {
                if (!page) return;
                onNavigate?.(page);
                onClose?.();
              }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-accentdim text-accent font-medium"
                  : page
                  ? "text-muted hover:bg-panel2 hover:text-slate-200"
                  : "text-muted/50 cursor-default"
              }`}
            >
              <Icon size={17} />
              {label}
            </button>
          );
        })}
      </nav>

      <div className="px-4 pb-4 space-y-4 border-t border-border pt-4">
        <div className="text-xs font-semibold text-muted tracking-wide">FILTROS</div>
        <div>
          <label className="block text-xs text-muted mb-1">Ligas</label>
          <select
            value={selectedLeague}
            onChange={(e) => onLeagueChange(e.target.value)}
            className="w-full bg-panel2 border border-border rounded-md text-sm px-2 py-1.5 text-slate-200"
          >
            <option value="Todas">Todas</option>
            {leagues.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted">Apenas Value Bets</span>
          <button
            onClick={onToggleValueBets}
            className={`w-10 h-5 rounded-full relative transition-colors ${
              onlyValueBets ? "bg-accent" : "bg-panel2 border border-border"
            }`}
          >
            <span
              className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${
                onlyValueBets ? "left-5" : "left-0.5"
              }`}
            />
          </button>
        </div>
      </div>

      <div className="px-4 py-4 border-t border-border flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-accentdim text-accent flex items-center justify-center font-semibold">
          {"A"}
        </div>
        <div>
          <div className="text-sm text-slate-200 leading-tight">Analista Pro</div>
          <div className="text-[11px] text-accent flex items-center gap-1">
            Plano Premium <Crown size={11} />
          </div>
        </div>
      </div>
      </aside>
    </>
  );
}
