---
name: pirx-data-pipeline
description: PIRX data pipeline from raw wearable ingestion through data cleaning, Celery background tasks, feature engineering with rolling windows, ACWR computation, structural shift detection, projection engine updates, bias correction, and embedding generation. Use when implementing or modifying sync pipelines, task queues, feature computation, projection recompute triggers, data cleaning filters, or notification logic in the PIRX app.
---

# PIRX Data Pipeline

## Pipeline Overview

```
Raw Wearable Data → Data Cleaning → Feature Engineering →
Structural Shift Check → Projection Recompute → Embedding Generation →
Frontend Update (Supabase Realtime)
```

## Celery Task Architecture

Celery 5.x with Redis broker. Four dedicated queues:

```python
CELERY_CONFIG = {
    'broker_url': 'redis://...',
    'result_backend': 'redis://...',
    'task_serializer': 'json',
    'timezone': 'UTC',
    'task_routes': {
        'pirx.tasks.projection.*': {'queue': 'projection'},
        'pirx.tasks.ml.*': {'queue': 'ml'},
        'pirx.tasks.sync.*': {'queue': 'sync'},
        'pirx.tasks.chat.*': {'queue': 'chat'},
    },
    'task_time_limit': 300,
    'task_soft_time_limit': 240,
}
```

## Task Registry

| Task | Queue | Priority | Trigger | Duration |
|---|---|---|---|---|
| `feature_engineering` | projection | High | Activity sync webhook | 2-5 sec |
| `recompute_projection` | projection | High | Feature shift ≥ 2 sec | 5-15 sec |
| `train_user_model` | ml | Low | Weekly or 20+ new activities | 30-120 sec |
| `generate_embeddings` | chat | Medium | Projection change, insight | 1-3 sec |
| `structural_decay_check` | projection | Medium | Daily pg_cron | 1 sec/user |
| `weekly_summary` | sync | Low | Weekly cron | 5-10 sec/user |
| `wearable_backfill` | sync | Low | New wearable connection | 30-300 sec |
| `bias_correction` | ml | Low | Monthly cron | 10-30 sec/user |

## Data Cleaning Pipeline

Applied to every incoming activity before feature engineering. Based on Dash 2024 research — improved model performance by 12%.

```python
def clean_activity(activity: dict) -> Optional[dict]:
    if activity['activity_type'] != 'run':
        return None
    if activity['duration_seconds'] < 180:
        return None  # < 3 min
    if activity['distance_meters'] < 1600:
        return None  # < 1.6 km
    pace = activity['duration_seconds'] / (activity['distance_meters'] / 1000)
    if pace > runner_avg_pace * 1.5:
        return None  # likely mislabeled walk
    if pace < 223:
        return None  # faster than 3:43/km — likely bike/ski
    if activity.get('elevation_gain_m') == 0 and activity.get('distance_meters', 0) > 5000:
        return None  # missing elevation on long run
    return activity
```

## Feature Engineering Pipeline

Five feature domains computed from rolling windows:

```python
FEATURE_DOMAINS = {
    'volume': [
        'rolling_distance_7d', 'rolling_distance_21d', 'rolling_distance_42d',
        'sessions_per_week', 'long_run_count',
    ],
    'intensity': [
        'z1_pct', 'z2_pct', 'z3_pct', 'z4_pct', 'z5_pct',
        'threshold_density_min_week', 'speed_exposure_min_week',
    ],
    'efficiency': [
        'matched_hr_band_pace', 'hr_drift_sustained',
        'late_session_pace_decay',
    ],
    'consistency': [
        'weekly_load_stddev', 'block_variance',
        'session_density_stability', 'acwr_4w', 'acwr_6w', 'acwr_8w',
    ],
    'physiological': [
        'resting_hr_trend', 'hrv_trend', 'sleep_score_trend',
    ],
}
```

### Rolling Window Weights

| Window | Weight |
|---|---|
| Recent 7 days | 0.45 |
| Days 8–21 | 0.35 |
| Days 22–90 | 0.20 |

## Structural Shift Threshold

Projection recompute triggers ONLY when the new computation differs from current by **≥ 2 seconds**. Below threshold, only the feature cache updates. This prevents micro-updates from creating noise.

## Projection Update Flow

1. Load per-user model (LSTM or Gradient Boosting depending on data maturity)
2. Compute new driver states (5 drivers: Aerobic Base, Threshold Density, Speed Exposure, Running Economy, Load Consistency)
3. **Drivers MUST sum to total improvement** — no rounding errors allowed
4. Apply volatility dampening: `smoothed = α × new + (1 - α) × previous` where α ∈ [0.3, 0.7]
5. Store new `Projection_State` and `Driver_State` rows (immutable append)
6. Generate embedding of projection change for chat RAG
7. Supabase Realtime notifies frontend

## ACWR Computation (Multi-Window)

```python
def compute_acwr(loads: List[float], acute_days=7, chronic_days=28) -> float:
    acute = ewma(loads[-acute_days:], span=acute_days)
    chronic = ewma(loads[-chronic_days:], span=chronic_days)
    return acute / chronic if chronic > 0 else 1.0

acwr_4w = compute_acwr(loads, 7, 28)
acwr_6w = compute_acwr(loads, 7, 42)
acwr_8w = compute_acwr(loads, 7, 56)
```

| Zone | ACWR Range | Interpretation |
|---|---|---|
| Safe | 0.8–1.3 | Optimal training load |
| Injury risk | > 1.5 | Elevated injury risk |
| Detraining | < 0.6 | Fitness loss |

## Structural Decay

Triggered when no activity for ≥ 10 days:

- Apply bounded decay factor to projection
- Widen volatility / Supported Range
- Decrease Readiness score
- Checked via daily `pg_cron` job calling `structural_decay_check` task

## Bias Correction Loop

Monthly cron task. Based on Biró et al. 2024 — iterative correction until convergence:

```python
epsilon = 0.01
while True:
    bias = mean(predicted - actual)
    corrected = predicted - bias
    new_error = mean(abs(corrected - actual))
    if abs(new_error - prev_error) < epsilon:
        break
    prev_error = new_error
```

## Embedding Generation

On every projection change or notable insight:

1. Compose text summary of what changed
2. Embed via `text-embedding-3-small` (1536d)
3. Store in `user_embeddings` table with `content_type` tag

Content types: `activity_summary`, `projection_change`, `insight`, `driver_shift`

## Feature Cache (Redis)

Pre-computed rolling features cached with key pattern:

```
pirx:features:{user_id}:{feature_name}
```

- **TTL**: 24 hours
- Recomputed on each activity sync

## Notification Triggers

Push notification ONLY when:

- Projection shifts ≥ 2 seconds
- Readiness shifts ≥ 5 points
- Adjunct reaches emerging threshold

No daily micro-alerts.

## Non-Interference Rules

1. Only the projection engine writes to projection state
2. Drivers must sum to total improvement — no rounding errors
3. Adjunct analysis runs parallel — never feeds back into projection
4. Wearable sync writes raw data only
5. Chat agent is read-only for projection state

## Dependencies

`celery[redis]`, `redis`, `numpy`, `pandas`, `scipy`, `scikit-learn`, `torch`, `openai`
