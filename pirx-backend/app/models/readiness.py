from pydantic import BaseModel


class EventReadiness(BaseModel):
    event: str
    score: float
    stage: str


class ReadinessResponse(BaseModel):
    events: list[EventReadiness]
