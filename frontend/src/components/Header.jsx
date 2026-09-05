import { Bell, RefreshCw, Clock, Menu } from "lucide-react";

export default function Header({
  lastUpdate,
  onRefresh,
  refreshing,
  onOpenSidebar,
  title = "DASHBOARD",
  subtitle = "Visão geral e recomendações em tempo real",
}) {
  return (
    <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-4 sm:px-6 py-4 sm:py-5 border-b border-border">
      <div className="flex items-center gap-3">
        {/* Botao de menu: so aparece em telas pequenas (abaixo de md), abre a
            barra lateral como gaveta. Em telas md+ a barra ja fica sempre
            visivel, entao este botao some. */}
        <button
          onClick={onOpenSidebar}
          className="md:hidden text-muted hover:text-slate-200 shrink-0"
          aria-label="Abrir menu"
        >
          <Menu size={22} />
        </button>
        <div>
          <h1 className="text-lg sm:text-xl font-semibold text-slate-100 tracking-tight">{title}</h1>
          <p className="text-xs sm:text-sm text-muted flex items-center gap-1.5 flex-wrap">
            {subtitle}
            <span
              className="inline-flex items-center gap-1 text-[11px] text-accent bg-accentdim px-2 py-0.5 rounded-full"
              title="O sistema coleta novas estatísticas das partidas ao vivo e recalcula as recomendações automaticamente a cada 5 minutos."
            >
              <Clock size={11} />
              Coleta automática a cada 5 min
            </span>
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3 sm:gap-4 flex-wrap justify-between sm:justify-end">
        <button className="relative text-muted hover:text-slate-200 shrink-0">
          <Bell size={19} />
          <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-accent" />
        </button>
        <span className="text-xs text-muted whitespace-nowrap">
          Última atualização: {lastUpdate}
          <span className="relative inline-flex w-1.5 h-1.5 ml-1.5 align-middle">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
            <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-accent" />
          </span>
        </span>
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 bg-accent text-black text-sm font-medium px-4 py-2 rounded-lg hover:brightness-110 disabled:opacity-60 shrink-0"
        >
          <RefreshCw size={15} className={refreshing ? "animate-spin" : ""} />
          ATUALIZAR
        </button>
      </div>
    </header>
  );
}
