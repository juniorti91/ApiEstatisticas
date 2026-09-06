from pydantic import BaseModel


class WinProbabilityOut(BaseModel):
    home: float
    draw: float
    away: float


class NextGoalOut(BaseModel):
    home: float
    away: float


class GoalWindowOut(BaseModel):
    home_5min: float
    away_5min: float
    home_10min: float
    away_10min: float


class MomentumOut(BaseModel):
    home: float | None = None
    away: float | None = None
    home_delta: float | None = None
    away_delta: float | None = None
    home_trend: str = "indisponivel"
    away_trend: str = "indisponivel"


class AnomalyRowOut(BaseModel):
    label: str
    home_pct: float | None = None
    away_pct: float | None = None


class PrognosticsOut(BaseModel):
    minute: int
    # True quando a partida ainda nao tem minutos suficientes pra confiar
    # no modelo (ver MIN_MINUTE_FOR_PROGNOSTICS no router) - o frontend
    # mostra um aviso em vez das probabilidades nesse caso.
    insufficient_data: bool = False
    win_probability: WinProbabilityOut
    next_goal: NextGoalOut
    goal_windows: GoalWindowOut
    momentum: MomentumOut
    anomalies: list[AnomalyRowOut] = []
