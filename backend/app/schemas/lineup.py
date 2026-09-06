from pydantic import BaseModel


class LineupPlayerOut(BaseModel):
    number: int | None = None
    name: str
    pos: str = ""
    # "linha:posicao" (ex: "2:3") - None quando a API nao informou.
    grid: str | None = None


class InjuryOut(BaseModel):
    player_name: str
    reason: str
    type: str = ""


class MatchLineupOut(BaseModel):
    referee: str | None = None
    formation_home: str | None = None
    formation_away: str | None = None
    coach_home: str | None = None
    coach_away: str | None = None
    lineup_home: list[LineupPlayerOut] = []
    lineup_away: list[LineupPlayerOut] = []
    substitutes_home: list[LineupPlayerOut] = []
    substitutes_away: list[LineupPlayerOut] = []
    injuries_home: list[InjuryOut] = []
    injuries_away: list[InjuryOut] = []
    # False quando a API-Football ainda nao publicou a escalacao dessa
    # partida (comum ate ~1h antes do apito) - frontend mostra um aviso em
    # vez de uma tela vazia sem explicacao.
    lineup_available: bool = False

    model_config = {"from_attributes": True}
