from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProjectionResponse(BaseModel):
    event: str
    projected_time_seconds: float
    projected_time_display: str  # "19:42" format
    supported_range_low: float
    supported_range_high: float
    supported_range_display: str  # "19:15 – 20:08" format
    baseline_time_seconds: float
    total_improvement_seconds: float
    volatility: float
    last_updated: Optional[str] = None
    model_source: Optional[str] = None
    model_confidence: Optional[float] = None
    fallback_reason: Optional[str] = None


class ProjectionHistoryPoint(BaseModel):
    date: str
    projected_time_seconds: float
    event: str
    range_low: Optional[float] = None
    range_high: Optional[float] = None


class ProjectionHistoryResponse(BaseModel):
    event: str
    days: int
    history: list[ProjectionHistoryPoint]


class TrajectoryScenario(BaseModel):
    label: str  # "Maintain", "Push", "Ease Off"
    projected_time_seconds: float
    projected_time_display: str
    description: str
    confidence: Optional[float] = None  # 0-1
    delta_seconds: Optional[float] = None  # positive = faster than current


class TrajectoryResponse(BaseModel):
    event: str
    scenarios: list[TrajectoryScenario]


class DriverSummary(BaseModel):
    driver_name: str
    display_name: str
    contribution_seconds: float
    score: float  # 0-100
    trend: str  # "improving", "stable", "declining"
    trend_emoji: str  # "↑", "→", "↓"


class DriversResponse(BaseModel):
    event: str
    drivers: list[DriverSummary]
    total_improvement_seconds: float


class DriverDetailPoint(BaseModel):
    date: str
    score: float


class DriverDetailResponse(BaseModel):
    driver_name: str
    display_name: str
    description: str
    score: float
    trend: str
    contribution_seconds: float
    history: list[DriverDetailPoint]


class DriverExplanation(BaseModel):
    driver_name: str
    top_factors: list[dict]  # [{"feature": "z4_pct", "impact": 0.35, "direction": "positive"}]
    summary: str
