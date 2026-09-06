from datetime import datetime

from pydantic import BaseModel


class TeamHistoryMatchOut(BaseModel):
    fixture_api_id: int
    opponent_name: str
    is_home: bool
    league_api_id: int
    league_name: str
    played_at: datetime
    goals_for: int
    goals_against: int
    ht_goals_for: int | None = None
    ht_goals_against: int | None = None

    model_config = {"from_attributes": True}
