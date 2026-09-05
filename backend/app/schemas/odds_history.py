from datetime import datetime

from pydantic import BaseModel


class OddsHistoryPointOut(BaseModel):
    minute: int
    captured_at: datetime
    odd: float
    estimated_probability: float

    model_config = {"from_attributes": True}
