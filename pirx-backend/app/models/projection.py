from datetime import datetime

from pydantic import BaseModel


class ProjectionResponse(BaseModel):
    event: str
    midpoint_seconds: float
    range_lower: float
    range_upper: float
    confidence_score: float
    volatility_score: float
    improvement_since_baseline: float
    twenty_one_day_change: float
    status: str
    computed_at: datetime


class ProjectionHistoryPoint(BaseModel):
    date: datetime
    midpoint_seconds: float
    range_lower: float
    range_upper: float


class TrajectoryScenario(BaseModel):
    label: str
    projected_seconds: float
