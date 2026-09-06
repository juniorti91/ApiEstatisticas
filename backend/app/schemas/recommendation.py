from datetime import datetime

from pydantic import BaseModel


class RecommendationOut(BaseModel):
    id: int
    fixture_id: int
    market: str
    selection: str
    team_focus: str
    line: float
    odd: float
    # None = registro antigo, gravado antes desta coluna existir (estado
    # desconhecido) - ver comentario em app/models/recommendation.py.
    odd_is_live: bool | None = None
    estimated_probability: float
    implied_probability: float
    expected_value: float
    confidence_stars: int
    is_value_bet: bool
    justification: str
    minute_recommended: int
    created_at: datetime
    status: str
    settled_at: datetime | None
    final_stat_value: float | None
    is_primary: bool

    model_config = {"from_attributes": True}


class RecommendationHistoryRow(BaseModel):
    id: int
    fixture_label: str
    played_on: datetime
    selection: str
    odd: float
    status: str
    result_score: str | None = None
