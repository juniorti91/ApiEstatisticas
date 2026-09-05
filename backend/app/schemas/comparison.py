from pydantic import BaseModel


class ComparisonMetric(BaseModel):
    label: str
    home_avg_last: float
    away_avg_last: float
    home_current: float
    away_current: float
    home_trend: str  # "up" | "down" | "flat" (current vs media)
    away_trend: str


class MatchComparison(BaseModel):
    sample_size: int
    metrics: list[ComparisonMetric]
