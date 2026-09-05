"""
Orquestra os jobs em background com APScheduler:

  * scan_job      -> a cada LIVE_SCAN_INTERVAL_MINUTES: descobre partidas
                     ao vivo novas nas ligas monitoradas.
  * collect_job   -> a cada COLLECTOR_INTERVAL_MINUTES (padrao 5): grava
                     um snapshot de cada partida monitorada, gera/atualiza
                     as recomendacoes e confere partidas que terminaram.

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
    async with AsyncSessionLocal() as session:
        try:
            await collect_snapshots(session)
            await generate_recommendations_for_all_live(session)
            await settle_finished_fixtures(session)
        except Exception:  # noqa: BLE001
            logger.exception("Erro no ciclo de coleta/recomendacao")


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
    scheduler.start()
    logger.info(
        "Scheduler iniciado: scan a cada %dmin, coleta a cada %dmin.",
        settings.live_scan_interval_minutes,
        settings.collector_interval_minutes,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
