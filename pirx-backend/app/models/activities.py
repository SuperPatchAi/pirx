from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NormalizedActivity(BaseModel):
    source: str
    timestamp: datetime
    duration_seconds: int
    distance_meters: float
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    avg_pace_sec_per_km: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    calories: Optional[int] = None
    activity_type: str
    hr_zones: Optional[list[float]] = None
    laps: Optional[list[dict]] = None
    fit_file_url: Optional[str] = None
