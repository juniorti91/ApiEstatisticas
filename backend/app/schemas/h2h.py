from pydantic import BaseModel


class H2HMatchOut(BaseModel):
    fixture_api_id: int
    date: str | None = None
    league_name: str = ""
    home_name: str = "?"
    away_name: str = "?"
    home_goals: int | None = None
    away_goals: int | None = None


class H2HOut(BaseModel):
    matches: list[H2HMatchOut] = []
