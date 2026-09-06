from __future__ import annotations

from fastapi import APIRouter

from app.config import settings as app_config
from app.schemas.settings import AppSettingsOut

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=AppSettingsOut)
async def read_settings():
    """So leitura - os tres intervalos abaixo agora so podem ser mudados
    no .env (por pedido explicito do usuario, sem edicao pela tela). Este
    endpoint existe so para os badges do cabecalho mostrarem os valores
    reais em vigor, em vez de um texto fixo que pode ficar desatualizado
    se alguem mudar o .env depois."""
    return AppSettingsOut(
        odds_refresh_interval_seconds=app_config.odds_refresh_interval_seconds,
        collector_interval_minutes=app_config.collector_interval_minutes,
        live_scan_interval_minutes=app_config.live_scan_interval_minutes,
    )
