# PIRX Technical Reference

## Data Schema

### Users Table
| Field | Type |
|---|---|
| user_id | UUID |
| email | string |
| created_at | timestamp |
| primary_event | string |
| baseline_event_id | FK |
| projection_state_id | FK |

### Activities Table
| Field | Type |
|---|---|
| activity_id | UUID |
| user_id | FK |
| timestamp | datetime |
| duration_seconds | int |
| distance_meters | float |
| avg_hr | int |
| max_hr | int |
| avg_pace | float |
| elevation_gain | float |
| device_source | string |
| activity_type | enum: easy, threshold, interval, race, cross-training |
| adjunct_tags | array |

### Intervals Table (optional deep granularity)
| Field | Type |
|---|---|
| interval_id | UUID |
| activity_id | FK |
| duration_seconds | int |
| avg_pace | float |
| avg_hr | int |

### Physiology Table
| Field | Type |
|---|---|
| entry_id | UUID |
| user_id | FK |
| timestamp | datetime |
| resting_hr | int |
| hrv | float |
| sleep_score | float |
| confidence_score | float |
| fatigue_score | float |
| focus_score | float |
| notes | text |
| blood_lactate_rest | float |
| blood_lactate_easy | float |
| blood_lactate_threshold | float |
| blood_lactate_race | float |
| hemoglobin | float |
| hematocrit | float |
| ferritin | float |
| rbc | float |
| iron | float |
| vitamin_d | float |
| testosterone | float |

### Projection_State Table
| Field | Type |
|---|---|
| projection_id | UUID |
| user_id | FK |
| date | date |
| event | string |
| midpoint_seconds | float |
| range_lower | float |
| range_upper | float |
| confidence_score | float |
| volatility_score | float |

### Driver_State Table
| Field | Type |
|---|---|
| driver_id | UUID |
| projection_id | FK |
| aerobic_base_seconds | float |
| threshold_density_seconds | float |
| speed_exposure_seconds | float |
| load_consistency_seconds | float |
| running_economy_seconds | float |

### Adjunct_State Table
| Field | Type |
|---|---|
| adjunct_id | UUID |
| user_id | FK |
| adjunct_name | string |
| sessions_analyzed | int |
| median_projection_delta | float |
| hr_drift_delta | float |
| volatility_delta | float |
| statistical_status | enum: observational, emerging, supported |

## Feature Engineering

### Volume Features
- 7-day, 21-day, 42-day rolling volume
- Volume variance

### Intensity Features
- Z1–Z5 distribution percentages
- Threshold density (Z4 time/week)
- Speed exposure (Z5 time/week)

### Efficiency Features
- Matched HR band pace
- HR drift in sustained efforts
- Late-session pace decay

### Consistency Features
- Weekly load deviation
- Block variance
- Session density stability

## Projection Engine

### Core Formula

```
Projected Time = Baseline Time
                 - Aerobic Adjustment
                 - Threshold Adjustment
                 - Speed Adjustment
                 - Economy Adjustment
                 - Consistency Adjustment
```

All adjustments measured in seconds. Drivers sum to total improvement.

### Rolling Window Weights
| Window | Weight |
|---|---|
| Recent 7 days | 0.45 |
| Days 8-21 | 0.35 |
| Days 22-90 | 0.20 |

### Driver Calculations

- **Aerobic Base**: Function of 21-day volume relative to baseline volume. Converted to seconds via calibrated regression constant.
- **Threshold Density**: Function of Z4 minutes/week relative to baseline block. Uses pace near LT2 band and duration consistency.
- **Speed Exposure**: Function of Z5 minutes and max sustainable pace exposure. Short interval frequency factored.
- **Running Economy**: Matched HR band pace difference vs baseline. Scaled to event distance. Volatility filter applied.
- **Load Consistency**: Standard deviation of weekly load. High variance increases projection volatility.

### Supported Range Calculation

Range width determined by: volatility, driver imbalance, session density, race proximity.

```
Lower bound = Projected Time - (range_width / 2)
Upper bound = Projected Time + (range_width / 2)
```

### Volatility Dampening

If HR spike, illness flag, or large weekly load spike detected:

```
Smoothed projection = α × new_projection + (1 - α) × previous_projection
Where α ∈ [0.3, 0.7]
```

### Event Scaling (Cross-Distance)

```
T2 = T1 × (D2 / D1) ^ exponent
```

Exponent is dynamic based on aerobic dominance vs threshold dominance. 1500→3000 scaling differs from 3000→10K.

### Race Recalibration

When race_flag = true:
1. Replace baseline anchor
2. Recompute rolling structure
3. Projection recalculates immediately
4. Display: "Model Recalibrated"

### Readiness Score

```
Readiness = weighted composite of:
  - Structural alignment score
  - Specificity score
  - Volatility modifier
  - Durability factor
Smoothed via rolling EMA. Bounded 0-100.
```

Does NOT modify projection.

### 2-Week Trajectory

Uses short-term derivative of threshold density, volume, and efficiency trends. Simulates 3 scenarios:
- Maintain structure
- Increase threshold density
- Reduce load

Bounded to ±1.5% of current projection. Never overrides main projection.

## API Contract (Simplified)

```
GET /projection
  → midpoint, range_lower, range_upper, confidence,
    change_21_days, change_since_baseline

GET /drivers
  → driver_seconds, 21_day_trend (per driver)

GET /readiness
  → event_scores (per event)

GET /physiology
  → trend_arrays (HR, HRV, sleep, blood work)
```

## Update Triggers

### Workout Sync
1. Recompute rolling features
2. Check structural shift threshold
3. If threshold met → recompute projection
4. Update driver states
5. Update readiness
6. Store new projection state

### Race Sync
1. Anchor race
2. Recalibrate volatility
3. Recompute driver scaling
4. Store projection state

### No Activity >= 10 Days
- Apply structural decay factor (bounded)
- Volatility widens
- Readiness decreases

## Notification Rules

Trigger only when:
- Projection shifts >= 2 seconds
- Readiness shifts >= 5 points
- Adjunct reaches emerging threshold

No daily micro-alerts.

## Edge Cases

| Scenario | Behavior |
|---|---|
| No race history | Auto-estimate baseline from sustained efforts. Confidence lower. |
| Sparse data | Projection stable. Confidence reduced. Range widened. |
| High volatility | Range widened. Projected Time unchanged unless threshold met. |
| Baseline changed | Recalculate Improvement Since Baseline only. Projection unchanged. |

## Strategic Gaps to Address

### Priority 1 — Existential
1. **Projection Explainability** — expandable "Why this number?" view tracing to each driver
2. **Onboarding Flow** — 5-screen sequence to first Fitness Snapshot reveal (7-day retention critical)
3. **Notification Architecture** — 6 core push triggers: projection update, readiness shift, intervention signal, weekly summary, race approaching, new insight

### Priority 2 — High Impact
4. **Social Layer** — shareable Race Prediction Card (Instagram Stories optimized), cohort benchmarking
5. **Wearable API Depth** — raw data streams from Garmin Connect IQ and COROS Open Platform
6. **Model Accuracy Framework** — published ±7 sec benchmark, mean absolute error tracking

### Priority 3 — Strategic
7. **Coach Dashboard (B2B)** — multi-athlete view, Phase 2 revenue tier
8. **Data Privacy Compliance** — PIPEDA (Canada), GDPR (EU), HIPAA-adjacent (US) for blood/lactate data
9. **Diagnostic Lab API** — LifeLabs (Canada), LabCorp/Quest (US) for automated blood work ingestion

## Competitive Positioning

| Competitor | Their Model | PIRX Difference |
|---|---|---|
| Garmin | VO2-based prediction, continuous updates with little smoothing | Structural projection anchored to real baseline races |
| Strava | Weighted training load fitness score | Driver attribution in seconds that sum to total improvement |
| WHOOP | Daily recovery/strain scoring | Event-specific race capacity modeling |
| TrainerRoad | Prescriptive training plans | Measures structure, does not coach |

## Adjunct Library (Preliminary)

- Super Patch variants (Victory, Focus, Peace)
- Carbon-plated shoes
- Bicarbonate
- Caffeine protocol
- Altitude exposure
- Strength block
- Heat adaptation
- Creatine
- Beta-alanine
- Iron supplementation
- Recovery devices

## Physiology Manual Entry Fields

### Blood Lactate
- Resting
- Post Easy Run
- Post Threshold
- Post Race

### Blood Work
- Hemoglobin, Hematocrit, Ferritin, RBC
- Iron, Vitamin D, Testosterone
- Custom fields

### Context Notes
- Free text per date
- Rating scale: Felt Easy / Moderate / Hard

## Onboarding Flow (Summary)

1. Connect Garmin / COROS / Strava (OAuth)
2. Pull 6-12 months history
3. Baseline selection (auto-detect if none)
4. Primary event selection
5. Immediate projection generated
6. Settings optional
