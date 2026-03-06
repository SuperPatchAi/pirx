---
name: training-load-response-modeling
description: Frameworks for quantifying training load, intensity distribution, and training response from wearable/fitness app data. Covers TRIMP, velocity-based load, 4-week block analysis, polarized vs pyramidal training detection, and ML-based response prediction. Use when implementing PIRX driver calculations, training load features, intensity distribution analysis, or the projection engine's rolling window computations.
---

# Training Load & Response Modeling

## PIRX Application

PIRX's projection engine converts raw training data into structural features. This skill provides the validated frameworks for that conversion.

## Training Response Quantification (Zrenner et al. 2021)

**Source**: 6,771 marathon finishers, Runtastic fitness app data.

### Velocity-Based Response Metric

The most practical response metric from unsupervised wearable data:

```
Δv10 = v10_block4 - v10_block1
```

Where `v10` = best 10km velocity within a 4-week training block. A positive Δv10 indicates fitness improvement.

**PIRX mapping**: This directly maps to PIRX's "21-Day Change" concept — measuring structural improvement over rolling windows.

### 4-Week Training Block Analysis

Divide the training window into blocks and compute per-block:

```python
for each block (4 weeks):
    total_distance = sum(workout_distances)
    total_time = sum(workout_durations)
    best_v10 = max(10km_segment_velocities)
    mean_velocity = weighted_avg(velocity_distribution)
    mean_hr = weighted_avg(hr_distribution)
```

### Velocity Normalization

Normalize all velocities relative to the athlete's reference performance:

```
v_normalized = v_actual / v_reference
```

This enables cross-athlete comparison and standardized zone definitions.

### Intensity Zone Definition

From velocity distribution relative to reference pace:

```
LIT (Low Intensity)  = time at v < 1.0 × v_reference
Threshold            = time at 1.0-1.2 × v_reference
HIT (High Intensity) = time at v > 1.2 × v_reference
```

### Key Finding: What Produces Improvement

Across 6,771 runners:
- **Faster marathon group**: Higher volume, higher LIT share
- **High response group**: Continuous increase in training velocity over 16 weeks
- **Optimal mix**: Maximize volume at low intensities + continuous speed increase + HIT ≤ 5% of volume

**PIRX application**: These findings validate PIRX's driver model — Aerobic Base (volume at LIT) and Threshold Density (Z4 time) are the primary performance drivers.

## Pyramidal vs. Polarized Training Detection (Qin et al. 2025)

**Source**: 120 recreational marathon runners, 16-week intervention.

### Intensity Distributions

| Model | Z1 (Low) | Z2 (Moderate) | Z3 (High) |
|---|---|---|---|
| **Pyramidal** | 70% | 20% | 10% |
| **Polarized** | 80% | 5% | 15% |

### ML-Based Response Prediction

Performance prediction formula from the study:

```
P(t) = f(Σ wi × TLi(t) × e^(-λ(t - ti)))
```

Where:
- `P(t)` = predicted performance at time t
- `TLi` = training load at session i
- `wi` = intensity-specific weighting factors
- `λ` = decay factor for training stimulus over time

### Four Response Clusters

ML clustering on 120 runners identified:

| Cluster | % of Athletes | Characteristics |
|---|---|---|
| Polarized responders | 31.5% | Better with 80/5/15 distribution |
| Pyramidal responders | 31.9% | Better with 70/20/10 distribution |
| Dual responders | 18.7% | Improve with either approach |
| Non-responders | 17.9% | Minimal improvement from standard protocols |

**Strongest predictor**: Training experience (r = 0.72) — novice athletes favor pyramidal; experienced athletes respond better to polarized.

**PIRX application**: This directly supports "What We're Learning About You" module. PIRX can classify a runner's response type and identify their optimal intensity distribution pattern.

## Training Load Metrics

### Session RPE Method (sRPE)

```
Session Load = RPE (1-10) × Duration (minutes)
```

### Heart Rate TRIMP (Training Impulse)

```
TRIMP = Duration × ΔHR_ratio × 0.64 × e^(1.92 × ΔHR_ratio)
```

Where `ΔHR_ratio = (HR_exercise - HR_rest) / (HR_max - HR_rest)`

### Exponential Weighted Moving Average (EWMA)

For acute and chronic load tracking:

```
Acute Load (7-day EWMA):
  L_acute(t) = L(t) × (2/(7+1)) + L_acute(t-1) × (1 - 2/(7+1))

Chronic Load (28-day EWMA):
  L_chronic(t) = L(t) × (2/(28+1)) + L_chronic(t-1) × (1 - 2/(28+1))
```

### Acute:Chronic Workload Ratio

```
ACWR = Acute Load / Chronic Load
```

- ACWR 0.8-1.3: Safe training zone
- ACWR > 1.5: Injury risk elevated
- ACWR < 0.6: Detraining risk

**PIRX application**: ACWR maps to PIRX's Load Consistency driver and volatility detection.

## Feature Engineering Pipeline

From the ML studies, the optimal feature set for runner performance prediction:

### Volume Features (align with PIRX Aerobic Base driver)
- 7-day, 21-day, 42-day rolling distance
- Number of sessions per week
- Long run count (>15km or >90min)

### Intensity Features (align with PIRX Threshold Density + Speed Exposure drivers)
- Z4 minutes per week (threshold density)
- Z5 minutes per week (speed exposure)
- Intensity distribution percentages

### Efficiency Features (align with PIRX Running Economy driver)
- Pace at matched HR band
- HR drift in sustained efforts
- Late-session pace decay

### Consistency Features (align with PIRX Load Consistency driver)
- Weekly load standard deviation
- Block-to-block variance
- Session density per week
- ACWR stability

## Δv10 HR Gating (Critical for Valid Response Measurement)

From Zrenner et al.: The Δv10 metric is only valid when both assessment runs (block 1 and block 4) were performed at **HR > 0.8 × HRmax**. Without this gate, easy runs contaminate the velocity comparison.

**PIRX must filter**: Only use runs where average HR ≥ 80% of max HR when computing velocity-based fitness changes.

## Training Effect Matrix (Qin et al. 2025)

Complete lookup table for personalized intensity distribution recommendation:

| Factor | Category | Pyramidal Δ | Polarized Δ | Optimal |
|---|---|---|---|---|
| Experience | Novice (<2 yr) | +12.4% | +5.8% | Pyramidal |
| Experience | Intermediate (2-5 yr) | +8.9% | +9.3% | Either |
| Experience | Advanced (5-8 yr) | +6.3% | +11.2% | Polarized |
| Experience | Elite (>8 yr) | +5.6% | +13.7% | Polarized |
| Age | 18-30 | +9.8% | +10.2% | Either |
| Age | 31-40 | +8.5% | +11.3% | Polarized |
| Age | 41-50 | +11.4% | +7.9% | Pyramidal |
| Age | >50 | +10.9% | +6.8% | Pyramidal |
| VO2max | <45 | +11.2% | +10.8% | Either |
| VO2max | 45-55 | +12.4% | +8.3% | Pyramidal |
| VO2max | >55 | +6.9% | +13.5% | Polarized |

**PIRX application**: Populate "What We're Learning About You" with this data. Classify the runner's optimal methodology.

## Volume Does NOT Predict Response (Zrenner et al.)

Across 6,771 runners, all η² values for volume metrics on training response were **< 0.012**. Volume alone does not predict who improves — **intensity distribution and progressive overload** matter more. PIRX driver weighting should reflect this.

## Multi-Window ACWR (Smyth et al. 2022)

Instead of a single 7:28 day ACWR, compute across multiple chronic windows:

```
ACWR_4w = Acute(7d) / Chronic(28d)
ACWR_6w = Acute(7d) / Chronic(42d)
ACWR_8w = Acute(7d) / Chronic(56d)
```

Multi-window provides richer Load Consistency signal than single-window approaches.

## DTW for Variable-Duration Workout Comparison (Biró et al. 2024)

Dynamic Time Warping aligns workouts of different durations for comparison:

```python
from dtaidistance import dtw
similarity = dtw.distance(workout_a_pace_series, workout_b_pace_series)
```

Solves the problem of comparing a 30-min easy run to a 90-min long run for fatigue trending.

## Decay Factor Calibration

The training stimulus decay factor `λ` in `e^(-λ(t - ti))` determines training effect half-life. From Qin et al., this should be calibrated per runner using **Bayesian optimization**, not set as a fixed constant.

## Model Performance Benchmarks

From the studies, target accuracy for PIRX:

| Metric | Benchmark |
|---|---|
| Marathon time prediction | MAE < 2.4% (KNN) to 5.6% (ANN) |
| 10km response prediction | Δv10 direction accurate for >66% of athletes |
| Training methodology prediction | R² = 0.87 for personalized model |
| Injury risk classification | Accuracy 0.98, ROC-AUC 0.97 (Random Forest) |
| 10km velocity ↔ marathon velocity | r = 0.77 (validates cross-distance projection) |
