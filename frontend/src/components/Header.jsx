import { useEffect, useState } from "react";
import { Bell, RefreshCw, Clock, Menu } from "lucide-react";
import { ApiClient } from "../api/client";

// Badges so informativas - os 3 intervalos automaticos (scan, coleta,
// odds) so podem ser mudados no .env (por pedido explicito do usuario,
// sem edicao pela tela) e exigem reiniciar o backend. Os valores aqui
// vem do backend (GET /api/settings) so pra nao ficarem desatualizados
// se alguem mudar o .env depois.
function IntervalBadge({ label, minutes, title }) {
  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] text-accent bg-accentdim px-2 py-0.5 rounded-full"
      title={title}
    >
      <Clock size={11} />
      {label} a cada {minutes ?? "…"} min
    </span>
  );
}

export default function Header({
  lastUpdate,
  onRefresh,
  refreshing,
  onOpenSidebar,
  title = "DASHBOARD",
  subtitle = "Visão geral e recomendações em tempo real",
}) {
  const [oddsMinutes, setOddsMinutes] = useState(null);
  const [statsMinutes, setStatsMinutes] = useState(null);

  useEffect(() => {
    let cancelled = false;
    ApiClient.getSettings()
      .then((data) => {
        if (cancelled) return;
        setOddsMinutes(data.odds_refresh_interval_minutes);
        setStatsMinutes(data.collector_interval_minutes);
      })
      .catch(() => {
        // Mantem os badges com "…" em vez de quebrar o cabecalho inteiro
        // se o backend estiver offline no primeiro carregamento.
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
            <IntervalBadge
              label="Estatísticas"
              minutes={statsMinutes}
              title="O sistema coleta todas as estatísticas das partidas ao vivo automaticamente nesse intervalo (para mudar, edite COLLECTOR_INTERVAL_MINUTES no .env e reinicie o backend)."
            />
            <IntervalBadge
              label="Odds"
              minutes={oddsMinutes}
              title="As odds ao vivo e as recomendações são reconsultadas nesse intervalo em todas as telas (para mudar, edite ODDS_REFRESH_INTERVAL_MINUTES no .env e reinicie o backend)."
            />
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
