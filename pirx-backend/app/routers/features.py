from fastapi import APIRouter, Depends

from app.dependencies import get_current_user

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


def _mock_features_history() -> list[dict]:
    """Shared mock feature history for learning/honest-state endpoints."""
    # TODO: Replace with real features_history loaded from Supabase
    return [
        {"weekly_load_stddev": 2500, "rolling_distance_21d": 85000, "z4_pct": 0.13, "z5_pct": 0.06, "acwr_4w": 1.1},
        {"weekly_load_stddev": 2800, "rolling_distance_21d": 88000, "z4_pct": 0.14, "z5_pct": 0.06, "acwr_4w": 1.15},
        {"weekly_load_stddev": 2200, "rolling_distance_21d": 92000, "z4_pct": 0.15, "z5_pct": 0.07, "acwr_4w": 1.1},
        {"weekly_load_stddev": 2400, "rolling_distance_21d": 95000, "z4_pct": 0.14, "z5_pct": 0.05, "acwr_4w": 1.05},
        {"weekly_load_stddev": 2300, "rolling_distance_21d": 97000, "z4_pct": 0.16, "z5_pct": 0.06, "acwr_4w": 1.08},
        {"weekly_load_stddev": 2100, "rolling_distance_21d": 100000, "z4_pct": 0.15, "z5_pct": 0.07, "acwr_4w": 1.12},
    ]


@router.get("/zones")
async def get_zone_distribution(user: dict = Depends(get_current_user)):
    """Get HR zone distribution and pace guide."""
    # TODO: Wire to real feature data from FeatureService / Supabase
    zones = [
        {"zone": "Z1", "name": "Recovery", "hr_range": "< 60% max HR", "pace_range": "6:30-7:30/km", "time_pct": 0.25},
        {"zone": "Z2", "name": "Easy Aerobic", "hr_range": "60-70% max HR", "pace_range": "5:30-6:30/km", "time_pct": 0.35},
        {"zone": "Z3", "name": "Tempo", "hr_range": "70-80% max HR", "pace_range": "4:50-5:30/km", "time_pct": 0.15},
        {"zone": "Z4", "name": "Threshold", "hr_range": "80-90% max HR", "pace_range": "4:10-4:50/km", "time_pct": 0.12},
        {"zone": "Z5", "name": "VO2max", "hr_range": "90-100% max HR", "pace_range": "< 4:10/km", "time_pct": 0.05},
    ]
    distribution_21d = {"z1": 0.25, "z2": 0.35, "z3": 0.18, "z4": 0.15, "z5": 0.07}
    return {
        "zones": zones,
        "distribution_21d": distribution_21d,
        "z2_efficiency_gain_sec_per_km": 3.2,
        "methodology": _compute_methodology(distribution_21d),
    }


@router.get("/economy")
async def get_running_economy(user: dict = Depends(get_current_user)):
    """Get running economy metrics."""
    # TODO: Wire to real computation from matched HR band analysis
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

    mock_features_history = _mock_features_history()
    insights = LearningModule.analyze_training_patterns(mock_features_history)
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
    # TODO: Load real adjunct data from activity_adjuncts + adjunct_state tables
    return {
        "adjuncts": [
            {
                "name": "Altitude Training",
                "sessions_analyzed": 8,
                "median_projection_delta_seconds": -4.2,
                "hr_drift_change_pct": -0.8,
                "volatility_change": -0.3,
                "status": "emerging",
                "confidence": 0.65,
            },
            {
                "name": "Strength Training",
                "sessions_analyzed": 12,
                "median_projection_delta_seconds": -2.1,
                "hr_drift_change_pct": -0.4,
                "volatility_change": 0.1,
                "status": "observational",
                "confidence": 0.45,
            },
            {
                "name": "Heat Acclimation",
                "sessions_analyzed": 4,
                "median_projection_delta_seconds": -1.8,
                "hr_drift_change_pct": -1.2,
                "volatility_change": 0.5,
                "status": "observational",
                "confidence": 0.35,
            },
        ]
    }


@router.get("/honest-state")
async def get_honest_state(user: dict = Depends(get_current_user)):
    """Get Current Honest State — what training data actually supports."""
    from app.ml.learning_module import LearningModule

    mock_features_history = _mock_features_history()
    insights = LearningModule.analyze_training_patterns(mock_features_history)
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
