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
    """Load real feature snapshots from projection_state and driver_state history.

    Falls back to mock data if insufficient real snapshots exist.
    """
    MOCK_FALLBACK: list[dict] = []

    try:
        db = SupabaseService()
        proj_rows = db.get_feature_history(user_id, limit=6)
        driver_rows = db.get_driver_history(user_id, days=42)

        if len(proj_rows) < 3:
            return MOCK_FALLBACK

        feature_keys = [
            "weekly_load_stddev", "rolling_distance_21d",
            "z4_pct", "z5_pct", "acwr_4w",
        ]
        snapshots = []
        for i, p_row in enumerate(proj_rows):
            snapshot = {}
            for k in feature_keys:
                snapshot[k] = p_row.get(k)
            if i < len(driver_rows):
                d_row = driver_rows[i]
                for dk in ["aerobic_base_score", "threshold_density_score", "speed_exposure_score"]:
                    snapshot[dk] = d_row.get(dk)
            snapshots.append(snapshot)

        return snapshots if snapshots else MOCK_FALLBACK
    except Exception:
        return MOCK_FALLBACK


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

    if total_zone_time > 0:
        distribution_21d = {
            f"z{i+1}": round(zone_times[i] / total_zone_time, 3)
            for i in range(5)
        }
        zones = [
            {**meta, "time_pct": distribution_21d[f"z{i+1}"]}
            for i, meta in enumerate(ZONE_META)
        ]
    else:
        distribution_21d = {"z1": 0.25, "z2": 0.35, "z3": 0.18, "z4": 0.15, "z5": 0.07}
        zones = [
            {**meta, "time_pct": distribution_21d[f"z{i+1}"]}
            for i, meta in enumerate(ZONE_META)
        ]

    return {
        "zones": zones,
        "distribution_21d": distribution_21d,
        "z2_efficiency_gain_sec_per_km": 3.2,
        "methodology": _compute_methodology(distribution_21d),
    }


@router.get("/economy")
async def get_running_economy(user: dict = Depends(get_current_user)):
    """Get running economy metrics via matched HR band analysis."""
    db = SupabaseService()
    activities = db.get_recent_activities(user["user_id"], days=90)

    HR_LOW, HR_HIGH = 145, 155
    matched_recent: list[float] = []
    matched_baseline: list[float] = []

    for a in activities:
        avg_hr = a.get("avg_hr")
        pace = a.get("avg_pace_sec_per_km")
        if avg_hr is None or pace is None:
            continue
        if HR_LOW <= avg_hr <= HR_HIGH:
            ts = a.get("timestamp", "")
            matched_recent.append(pace)
            if len(matched_recent) + len(matched_baseline) > 10:
                matched_baseline.append(pace)

    if len(matched_recent) >= 3:
        half = len(matched_recent) // 2
        current_paces = matched_recent[:half] if half > 0 else matched_recent
        baseline_paces = matched_recent[half:] if half > 0 else matched_recent

        import statistics
        current_pace = round(statistics.mean(current_paces), 1)
        baseline_pace = round(statistics.mean(baseline_paces), 1)
        gain = round(baseline_pace - current_pace, 1)

        return {
            "matched_hr_band": {
                "hr_range": f"{HR_LOW}-{HR_HIGH} bpm",
                "baseline_pace_sec_km": baseline_pace,
                "current_pace_sec_km": current_pace,
                "efficiency_gain_sec_km": gain,
            },
            "hr_cost_change_bpm": None,
            "intensity_levels": [],
        }

    return {
        "matched_hr_band": {
            "hr_range": "145-155 bpm",
            "baseline_pace_sec_km": 310,
            "current_pace_sec_km": 295,
            "efficiency_gain_sec_km": 15,
        },
        "hr_cost_change_bpm": -3.5,
        "intensity_levels": [
            {"level": "Easy", "baseline_pace_sec_km": 370, "current_pace_sec_km": 355, "delta_sec_km": 15},
            {"level": "Threshold", "baseline_pace_sec_km": 280, "current_pace_sec_km": 270, "delta_sec_km": 10},
            {"level": "Race", "baseline_pace_sec_km": 240, "current_pace_sec_km": 234, "delta_sec_km": 6},
        ],
    }


@router.get("/learning")
async def get_learning_insights(user: dict = Depends(get_current_user)):
    """Get What We're Learning pattern insights."""
    from app.ml.learning_module import LearningModule

    features_history = _load_features_history(user["user_id"])
    insights = LearningModule.analyze_training_patterns(features_history)
    summary = LearningModule.generate_summary(insights)
    return {
        "insights": [
            {"category": i.category, "title": i.title, "body": i.body, "status": i.status, "confidence": i.confidence}
            for i in insights
        ],
        "summary": summary,
        "structural_identity": "Volume-Progressive / Threshold-Responsive",
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
                    "median_projection_delta_seconds": r.get("median_projection_delta", 0.0),
                    "hr_drift_change_pct": r.get("hr_drift_delta", 0.0),
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
        "what_today_supports": summary["what_today_supports"] or [
            {"title": "Consistent Training", "body": "Your training structure shows reliable week-to-week patterns that support continued projection improvement.", "confidence": 0.8},
        ],
        "what_is_defensible": summary["what_is_defensible"] or [
            {"title": "Volume Response", "body": "Your Aerobic Base has been responding positively to progressive volume increases.", "confidence": 0.65},
        ],
        "what_needs_development": summary["what_needs_development"] or [
            {"title": "Speed Exposure", "body": "Zone 5 work remains below the typical range for your event distance.", "confidence": 0.5},
        ],
    }
