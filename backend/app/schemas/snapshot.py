from datetime import datetime

from pydantic import BaseModel


class MatchSnapshotOut(BaseModel):
    id: int
    fixture_id: int
    captured_at: datetime
    minute: int

    goals_home: int
    goals_away: int
    possession_home: float
    possession_away: float

    shots_on_target_home: int
    shots_on_target_away: int
    shots_off_target_home: int
    shots_off_target_away: int
    total_shots_home: int
    total_shots_away: int

    corners_home: int
    corners_away: int

    yellow_cards_home: int
    yellow_cards_away: int
    red_cards_home: int
    red_cards_away: int

    fouls_home: int
    fouls_away: int
    offsides_home: int
    offsides_away: int

    dangerous_attacks_home: int
    dangerous_attacks_away: int

    shots_blocked_home: int = 0
    shots_blocked_away: int = 0
    shots_inside_box_home: int = 0
    shots_inside_box_away: int = 0
    shots_outside_box_home: int = 0
    shots_outside_box_away: int = 0

    passes_total_home: int = 0
    passes_total_away: int = 0
    passes_accurate_home: int = 0
    passes_accurate_away: int = 0
    passes_pct_home: float = 0
    passes_pct_away: float = 0

    goalkeeper_saves_home: int = 0
    goalkeeper_saves_away: int = 0

    xg_home: float = 0
    xg_away: float = 0

    model_config = {"from_attributes": True}


class ManualSnapshotIn(BaseModel):
    """Payload para insercao manual de estatisticas (fallback sem API)."""

    minute: int
    goals_home: int = 0
    goals_away: int = 0
    possession_home: float = 50
    possession_away: float = 50
    shots_on_target_home: int = 0
    shots_on_target_away: int = 0
    shots_off_target_home: int = 0
    shots_off_target_away: int = 0
    total_shots_home: int = 0
    total_shots_away: int = 0
    corners_home: int = 0
    corners_away: int = 0
    yellow_cards_home: int = 0
    yellow_cards_away: int = 0
    red_cards_home: int = 0
    red_cards_away: int = 0
    fouls_home: int = 0
    fouls_away: int = 0
    offsides_home: int = 0
    offsides_away: int = 0
    dangerous_attacks_home: int = 0
    dangerous_attacks_away: int = 0
