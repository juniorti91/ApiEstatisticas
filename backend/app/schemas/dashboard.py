from pydantic import BaseModel


class PerformanceSummary(BaseModel):
    period_days: int
    hit_rate: float  # %
    hit_rate_delta: float  # variacao vs periodo anterior, em pontos percentuais
    roi: float  # %
    roi_delta: float
    profit_loss: float  # em unidades monetarias (assumindo stake padrao)
    stake_base: float
    total_recommendations: int
    value_bets_share: float  # %
