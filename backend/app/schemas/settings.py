from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    """Reflete os 3 intervalos automaticos configurados no .env - so
    leitura, usado pelos badges informativos do cabecalho do front."""

    odds_refresh_interval_seconds: int
    collector_interval_minutes: int
    live_scan_interval_minutes: int
