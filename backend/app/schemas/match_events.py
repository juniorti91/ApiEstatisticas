from pydantic import BaseModel


class MatchEventOut(BaseModel):
    minute: int
    extra_minute: int | None = None
    side: str  # "home" ou "away"
    type: str = ""
    detail: str = ""
    player_name: str | None = None
    assist_name: str | None = None


class MatchEventsOut(BaseModel):
    events: list[MatchEventOut] = []
