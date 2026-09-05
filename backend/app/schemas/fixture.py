from datetime import datetime

from pydantic import BaseModel


class TeamOut(BaseModel):
    id: int
    api_id: int
    name: str
    logo_url: str

    model_config = {"from_attributes": True}


class LeagueOut(BaseModel):
    id: int
    api_id: int
    name: str
    country: str
    logo_url: str

    model_config = {"from_attributes": True}


class FixtureOut(BaseModel):
    id: int
    api_fixture_id: int
    league: LeagueOut
    home_team: TeamOut
    away_team: TeamOut
    round: str
    kickoff_at: datetime
    status: str
    elapsed_minutes: int
    goals_home: int
    goals_away: int
    is_monitored: bool

    model_config = {"from_attributes": True}


class FixtureSummary(BaseModel):
    """Versao leve, usada em listagens (ex: historico)."""

    id: int
    home_team_name: str
    away_team_name: str
    league_name: str
    kickoff_at: datetime
    status: str

    model_config = {"from_attributes": True}
