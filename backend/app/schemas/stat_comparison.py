from pydantic import BaseModel


class StatComparisonRow(BaseModel):
    key: str
    label: str
    home: float
    away: float


class StatComparisonOut(BaseModel):
    # None = acumulado do jogo todo (ver app/services/stat_window_service.py).
    window_minutes: int | None
    from_minute: int
    to_minute: int
    rows: list[StatComparisonRow]
