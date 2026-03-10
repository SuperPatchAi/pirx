from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.services.supabase_client import SupabaseService

router = APIRouter()


def _compute_methodology(distribution: dict) -> str:
    """Determine training methodology from zone distribution."""
    z1 = distribution.get("z1", 0)
    z2 = distribution.get("z2", 0)
    z4 = distribution.get("z4", 0)
    z5 = distribution.get("z5", 0)
    low_intensity = z1 + z2
    high_intensity = z4 + z5
    if low_intensity > 0.75:
        return "Pyramidal"
    if low_intensity < 0.60 and high_intensity > 0.25:
        return "Polarized"
    return "Mixed"


def _load_features_history(user_id: str) -> list[dict]:
    """Compute feature snapshots at weekly intervals from real activity data."""
    from datetime import datetime, timedelta, timezone
    from app.models.activities import NormalizedActivity
    from app.services.cleaning_service import CleaningService
    from app.services.feature_service import FeatureService

    try:
        db = SupabaseService()
        raw = db.get_recent_activities(user_id, days=90)
        if not raw or len(raw) < 5:
            return []

        activities = [NormalizedActivity.from_db_dict(a) for a in raw]
        for a in activities:
            if a.timestamp and a.timestamp.tzinfo:
                a.timestamp = a.timestamp.replace(tzinfo=None)
        activities.sort(key=lambda a: a.timestamp or datetime.min)

        avg_pace = CleaningService.compute_runner_avg_pace(activities)
        now = datetime.now()
        snapshots = []

        for weeks_back in range(6, -1, -1):
            cutoff = now - timedelta(weeks=weeks_back)
            window = [a for a in activities if a.timestamp and a.timestamp <= cutoff]
            if len(window) < 3:
                continue
            cleaned = CleaningService.clean_batch(window, avg_pace)
            if len(cleaned) < 3:
                continue
            try:
                features = FeatureService.compute_all_features(
                    cleaned, reference_date=cutoff, user_id=user_id
                )
                snapshots.append(features)
            except Exception:
                continue

        return snapshots
    except Exception:
        return []


@router.get("/zones")
async def get_zone_distribution(user: dict = Depends(get_current_user)):
    """Get HR zone distribution and pace guide."""
    ZONE_META = [
        {"zone": "Z1", "name": "Recovery", "hr_range": "< 60% max HR", "pace_range": "6:30-7:30/km"},
        {"zone": "Z2", "name": "Easy Aerobic", "hr_range": "60-70% max HR", "pace_range": "5:30-6:30/km"},
        {"zone": "Z3", "name": "Tempo", "hr_range": "70-80% max HR", "pace_range": "4:50-5:30/km"},
        {"zone": "Z4", "name": "Threshold", "hr_range": "80-90% max HR", "pace_range": "4:10-4:50/km"},
        {"zone": "Z5", "name": "VO2max", "hr_range": "90-100% max HR", "pace_range": "< 4:10/km"},
    ]

    db = SupabaseService()
    activities = db.get_recent_activities(user["user_id"], days=21)

    total_zone_time = 0.0
    zone_times = [0.0] * 5
    for a in activities:
        hr_zones = a.get("hr_zones")
        if hr_zones and len(hr_zones) >= 5:
            for i in range(5):
                zone_times[i] += hr_zones[i]
                total_zone_time += hr_zones[i]

    if total_zone_time == 0:
        easy_count = 0
        moderate_count = 0
        hard_count = 0
        total_dur = 0.0
        for a in activities:
            avg_hr = a.get("avg_hr")
            max_hr = a.get("max_hr")
            dur = float(a.get("duration_seconds") or 0)
            if not avg_hr or dur <= 0:
                continue
            total_dur += dur
            est_max = max_hr if max_hr and max_hr > 150 else 190
            pct = avg_hr / est_max
            if pct < 0.70:
                easy_count += dur
            elif pct < 0.85:
                moderate_count += dur
            else:
                hard_count += dur

        if total_dur == 0:
            return None

        z1_pct = round(easy_count * 0.4 / total_dur, 3)
        z2_pct = round(easy_count * 0.6 / total_dur, 3)
        z3_pct = round(moderate_count * 0.5 / total_dur, 3)
        z4_pct = round(moderate_count * 0.5 / total_dur, 3)
        z5_pct = round(hard_count / total_dur, 3)
        distribution_21d = {"z1": z1_pct, "z2": z2_pct, "z3": z3_pct, "z4": z4_pct, "z5": z5_pct}
        zones = [
            {**meta, "time_pct": round(distribution_21d[f"z{i+1}"] * 100, 1)}
            for i, meta in enumerate(ZONE_META)
        ]
        distribution_array = [
            {"zone": f"Z{i+1}", "pct": round(distribution_21d[f"z{i+1}"] * 100, 1)}
            for i in range(5)
        ]
        return {
            "zones": zones,
            "distribution": distribution_array,
            "z2_efficiency_gain": round(z2_pct * 100, 1),
            "methodology": _compute_methodology(distribution_21d),
        }

    distribution_21d = {
        f"z{i+1}": round(zone_times[i] / total_zone_time, 3)
        for i in range(5)
    }
    zones = [
        {**meta, "time_pct": round(distribution_21d[f"z{i+1}"] * 100, 1)}
        for i, meta in enumerate(ZONE_META)
    ]
    distribution_array = [
        {"zone": f"Z{i+1}", "pct": round(distribution_21d[f"z{i+1}"] * 100, 1)}
        for i in range(5)
    ]

    return {
        "zones": zones,
        "distribution": distribution_array,
        "z2_efficiency_gain": round(distribution_21d.get("z2", 0) * 100, 1),
        "methodology": _compute_methodology(distribution_21d),
    }


def _format_pace(sec_per_km: float) -> str:
    """Convert seconds-per-km to 'M:SS/km' string."""
    m = int(sec_per_km) // 60
    s = int(sec_per_km) % 60
    return f"{m}:{s:02d}/km"


def _build_economy_band(hr_range: str, baseline_sec: float, current_sec: float) -> dict:
    gain = round(baseline_sec - current_sec, 1)
    return {
        "hr_range": hr_range,
        "baseline_pace": _format_pace(baseline_sec),
        "current_pace": _format_pace(current_sec),
        "efficiency_gain": gain,
    }


def _build_intensity_level(level: str, baseline_sec: float, current_sec: float) -> dict:
    return {
        "level": level,
        "baseline": _format_pace(baseline_sec),
        "current": _format_pace(current_sec),
        "delta": round(baseline_sec - current_sec, 1),
    }


@router.get("/economy")
async def get_running_economy(user: dict = Depends(get_current_user)):
    """Get running economy metrics via matched HR band analysis."""
    db = SupabaseService()
    activities = db.get_recent_activities(user["user_id"], days=90)

    HR_LOW, HR_HIGH = 145, 155
    matched_recent: list[float] = []

    for a in activities:
        avg_hr = a.get("avg_hr")
        pace = a.get("avg_pace_sec_per_km")
        if avg_hr is None or pace is None:
            continue
        if HR_LOW <= avg_hr <= HR_HIGH:
            matched_recent.append(pace)

    if len(matched_recent) < 3:
        return None

    half = len(matched_recent) // 2
    current_paces = matched_recent[:half] if half > 0 else matched_recent
    baseline_paces = matched_recent[half:] if half > 0 else matched_recent

    import statistics
    current_pace = round(statistics.mean(current_paces), 1)
    baseline_pace = round(statistics.mean(baseline_paces), 1)

    return {
        "matched_hr_band": _build_economy_band(f"{HR_LOW}-{HR_HIGH} bpm", baseline_pace, current_pace),
        "hr_cost_change": 0,
        "intensity_levels": [],
    }


@router.get("/learning")
async def get_learning_insights(user: dict = Depends(get_current_user)):
    """Get What We're Learning pattern insights."""
    from app.ml.learning_module import LearningModule

    features_history = _load_features_history(user["user_id"])
    insights = LearningModule.analyze_training_patterns(features_history)
    summary_sections = LearningModule.generate_summary(insights)

    supported_count = len(summary_sections.get("what_today_supports", []))
    emerging_count = len(summary_sections.get("what_is_defensible", []))
    obs_count = len(summary_sections.get("what_needs_development", []))
    total = supported_count + emerging_count + obs_count
    summary_text = (
        f"{total} pattern{'s' if total != 1 else ''} detected: "
        f"{supported_count} supported, {emerging_count} emerging, {obs_count} observational."
    ) if total > 0 else "Not enough data to detect training patterns yet."

    insight_list = [
        {"category": i.category, "title": i.title, "body": i.body, "status": i.status, "confidence": i.confidence}
        for i in insights
    ]

    structural_identity = None
    if insight_list:
        categories = {i["category"] for i in insight_list}
        parts = []
        if "response" in categories:
            parts.append("Volume-Progressive")
        if "trend" in categories:
            parts.append("Threshold-Responsive")
        if "consistency" in categories:
            parts.append("Load-Consistent")
        structural_identity = " / ".join(parts) if parts else None

    return {
        "insights": insight_list,
        "summary": summary_text,
        "structural_identity": structural_identity,
    }


@router.get("/adjuncts")
async def get_adjunct_analysis(user: dict = Depends(get_current_user)):
    """Get adjunct analysis data (altitude, strength, heat acclimation)."""
    try:
        db = SupabaseService()
        rows = db.get_adjunct_state(user["user_id"])
        if rows:
            adjuncts = [
                {
                    "name": r.get("adjunct_name", "Unknown"),
                    "sessions_analyzed": r.get("sessions_analyzed", 0),
                    "median_projection_delta": r.get("median_projection_delta", 0.0),
                    "hr_drift_change": r.get("hr_drift_delta", 0.0),
                    "volatility_change": r.get("volatility_delta", 0.0),
                    "status": r.get("statistical_status", "observational"),
                    "confidence": min(r.get("sessions_analyzed", 0) / 20.0, 1.0),
                }
                for r in rows
            ]
            return {"adjuncts": adjuncts}
    except Exception:
        pass

    return {"adjuncts": []}


@router.get("/honest-state")
async def get_honest_state(user: dict = Depends(get_current_user)):
    """Get Current Honest State — what training data actually supports."""
    from app.ml.learning_module import LearningModule

    features_history = _load_features_history(user["user_id"])
    insights = LearningModule.analyze_training_patterns(features_history)
    summary = LearningModule.generate_summary(insights)
    return {
        "what_today_supports": summary["what_today_supports"],
        "what_is_defensible": summary["what_is_defensible"],
        "what_needs_development": summary["what_needs_development"],
    }


@router.get("/weekly-volume")
async def get_weekly_volume(user: dict = Depends(get_current_user)):
    """Get this week's running volume grouped by day and intensity."""
    from datetime import datetime, timedelta, timezone

    db = SupabaseService()
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

    activities = db.get_recent_activities(user["user_id"], days=7)
    if not activities:
        return {"days": [], "total_km": 0}

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    buckets = {d: {"day": d, "easy": 0.0, "tempo": 0.0, "long": 0.0} for d in day_names}
    total_km = 0.0

    for a in activities:
        ts = a.get("timestamp")
        if not ts:
            continue
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
        else:
            dt = ts
        weekday = dt.weekday()
        if weekday > 6:
            continue
        day_key = day_names[weekday]
        dist_km = float(a.get("distance_meters") or 0) / 1000
        total_km += dist_km

        activity_type = (a.get("activity_type") or "easy").lower()
        if activity_type in ("threshold", "interval", "tempo"):
            buckets[day_key]["tempo"] += dist_km
        elif dist_km >= 15:
            buckets[day_key]["long"] += dist_km
        else:
            buckets[day_key]["easy"] += dist_km

    days = [buckets[d] for d in day_names]
    for d in days:
        d["easy"] = round(d["easy"], 1)
        d["tempo"] = round(d["tempo"], 1)
        d["long"] = round(d["long"], 1)

    return {"days": days, "total_km": round(total_km, 1)}


@router.get("/hr-trend")
async def get_hr_trend(user: dict = Depends(get_current_user)):
    """Get heart rate trend data for the last 14 days."""
    from datetime import datetime, timezone

    db = SupabaseService()
    activities = db.get_recent_activities(user["user_id"], days=14)
    if not activities:
        return {"points": [], "avg": None, "max": None}

    points = []
    hr_values = []
    max_hrs = []

    for a in activities:
        avg_hr = a.get("avg_hr")
        if not avg_hr:
            continue
        ts = a.get("timestamp", "")
        date_str = ts[:10] if isinstance(ts, str) else ""
        points.append({"date": date_str, "avg_hr": int(avg_hr)})
        hr_values.append(int(avg_hr))
        max_hr = a.get("max_hr")
        if max_hr:
            max_hrs.append(int(max_hr))

    points.sort(key=lambda p: p["date"])

    avg = round(sum(hr_values) / len(hr_values)) if hr_values else None
    peak = max(max_hrs) if max_hrs else (max(hr_values) if hr_values else None)

    return {"points": points, "avg": avg, "max": peak}
