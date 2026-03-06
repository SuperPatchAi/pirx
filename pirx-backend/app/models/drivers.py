from datetime import datetime

from pydantic import BaseModel


class DriverState(BaseModel):
    name: str
    contribution_seconds: float
    twenty_one_day_change: float
    stability: str


class DriversResponse(BaseModel):
    event: str
    total_improvement: float
    drivers: list[DriverState]


class DriverTrendPoint(BaseModel):
    date: datetime
    contribution_seconds: float
