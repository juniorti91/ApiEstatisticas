"""
Orquestra os jobs em background com APScheduler:

  * scan_job      -> a cada LIVE_SCAN_INTERVAL_MINUTES: descobre partidas
                     ao vivo novas nas ligas monitoradas.
  * collect_job   -> a cada COLLECTOR_INTERVAL_MINUTES: grava um snapshot
                     completo (estatisticas de time + de jogador) de cada
                     partida monitorada e confere partidas que terminaram.
  * odds_job      -> a cada ODDS_REFRESH_INTERVAL_SECONDS (em SEGUNDOS,
                     nao minutos): reconsulta as odds AO VIVO de verdade
                     (/odds/live - 1 unica chamada cobre todas as partidas
                     monitoradas de uma vez) e gera/recalcula as
                     recomendacoes com o snapshot mais recente ja salvo
                     (sem gastar chamadas de estatisticas de novo). Roda
                     bem mais frequente que os outros dois ciclos porque
                     agora e barato (1 chamada por ciclo, nao escala com o
                     numero de partidas) - e o que faz a odd na tela
                     parecer de verdade "ao vivo", quase em tempo real, em
                     vez de atualizar so a cada alguns minutos.

IMPORTANTE (corrigido - estava gastando cota da API a toa): antes,
collect_job TAMBEM chamava generate_recommendations_for_all_live (que
busca odds na API, 1 chamada por partida monitorada) - isso fazia a busca
de odds rodar em dobro sem ganhar nada em atualidade. Agora so o odds_job
gera recomendacoes - collect_job cuida so de estatisticas.

Os tres intervalos so podem ser mudados no .env (por pedido explicito do
usuario) - nao ha mais edicao pela tela; mudar exige editar o .env e
reiniciar o backend.

Cada job abre sua propria sessao de banco (AsyncSessionLocal) e a fecha
ao final, para nao segurar conexoes entre execucoes.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.collector import collect_snapshots, scan_live_fixtures
from app.services.recommendation_engine import generate_recommendations_for_all_live
from app.services.results_tracker import settle_finished_fixtures

logger = logging.getLogger("betanalyzer.scheduler")

scheduler = AsyncIOScheduler()


async def run_scan_cycle() -> None:
    async with AsyncSessionLocal() as session:
        try:
            await scan_live_fixtures(session)
        except Exception:  # noqa: BLE001 - job de background nunca pode derrubar o processo
            logger.exception("Erro no ciclo de scan de partidas ao vivo")


async def run_collection_cycle() -> None:
    """So estatisticas: grava o snapshot completo (time + jogador) de cada
    partida monitorada e confere partidas encerradas. NAO gera
    recomendacoes aqui - isso e responsabilidade exclusiva do
    run_odds_refresh_cycle abaixo, pra nao buscar odds em dobro (ver
    comentario no topo do arquivo)."""
    async with AsyncSessionLocal() as session:
        try:
            await collect_snapshots(session)
            await settle_finished_fixtures(session)
        except Exception:  # noqa: BLE001
            logger.exception("Erro no ciclo de coleta")


async def run_odds_refresh_cycle() -> None:
    """Unico lugar que gera/atualiza recomendacoes: reconsulta as odds ao
    vivo e recalcula usando o snapshot mais recente que ja estiver salvo
    (sem gastar chamadas de estatisticas de novo). E o que faz a odd
    parecer "ao vivo de verdade" em todas as telas."""
    async with AsyncSessionLocal() as session:
        try:
            await generate_recommendations_for_all_live(session)
        except Exception:  # noqa: BLE001
            logger.exception("Erro no ciclo de atualizacao de odds")


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        run_scan_cycle,
        trigger=IntervalTrigger(minutes=settings.live_scan_interval_minutes),
        id="scan_live_fixtures",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_collection_cycle,
        trigger=IntervalTrigger(minutes=settings.collector_interval_minutes),
        id="collect_snapshots",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_odds_refresh_cycle,
        trigger=IntervalTrigger(seconds=settings.odds_refresh_interval_seconds),
        id="refresh_odds",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler iniciado: scan a cada %dmin, coleta a cada %dmin, odds a cada %ds.",
        settings.live_scan_interval_minutes,
        settings.collector_interval_minutes,
        settings.odds_refresh_interval_seconds,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
