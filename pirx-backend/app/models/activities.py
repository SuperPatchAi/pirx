from datetime import datetime
from typing import Optional

from dateutil.parser import parse as parse_dt
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

    @classmethod
    def from_db_dict(cls, raw: dict) -> "NormalizedActivity":
        """Convert a DB activity row (dict) to NormalizedActivity.

        Handles extra DB columns, missing fields, and string timestamps.
        """
        ts = raw.get("timestamp") or raw.get("started_at")
        if isinstance(ts, str):
            ts = parse_dt(ts)
        if ts is not None and ts.tzinfo is not None:
            ts = ts.replace(tzinfo=None)

        return cls(
            source=raw.get("source") or "unknown",
            timestamp=ts,
            duration_seconds=raw.get("duration_seconds") or 0,
            distance_meters=raw.get("distance_meters") or 0.0,
            avg_hr=raw.get("avg_hr"),
            max_hr=raw.get("max_hr"),
            avg_pace_sec_per_km=raw.get("avg_pace_sec_per_km"),
            elevation_gain_m=raw.get("elevation_gain_m"),
            calories=raw.get("calories"),
            activity_type=raw.get("activity_type") or "run",
            hr_zones=raw.get("hr_zones"),
            laps=raw.get("laps"),
            fit_file_url=raw.get("fit_file_url"),
        )
