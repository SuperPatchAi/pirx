---
name: event-distance-scaling
description: Power law models and formulas for scaling running performance predictions across distances (1500m to marathon). Implements Riegel formula, modified Riegel, and individual power law exponents for PIRX event scaling engine. Use when implementing cross-distance projection, event scaling, or distance-specific prediction logic.
---

# Event Distance Scaling

## PIRX Application

PIRX's projection engine scales a baseline race across distances (1500m, 3000m, 5K, 10K). This skill provides the research-backed formulas and models for that scaling.

## Core Formula: Riegel Power Law

The foundational cross-distance prediction model used across running science:

```
T2 = T1 × (D2 / D1) ^ exponent
```

Where:
- `T1` = known race time (seconds)
- `D1` = known race distance (meters)
- `T2` = predicted race time at target distance
- `D2` = target distance (meters)
- `exponent` = fatigue factor (default 1.06 for world-class; varies per individual)

**Source**: Riegel 1981, validated across 50+ years of data.

## Individual Power Law Exponents

Blythe & Király (2016) demonstrated that individual runners have their own power law exponent `λ1` that describes their speed-to-endurance balance. Key findings from 164,746 runners and 1,417,432 performances:

```
log(time) = λ1 × f1(distance) + λ2 × f2(distance) + λ3 × f3(distance)
```

**Three-component model per runner:**

| Component | Interpretation | Affects |
|---|---|---|
| `λ1` | Overall endurance level (individual power law exponent) | All distances > 800m |
| `λ2` | Speed-vs-endurance balance | Short/long distance divergence |
| `λ3` | Middle-distance specialization | 800m-10K transition behavior |

**Component values (f1, f2, f3) for standard distances:**

| Distance | f1 | f2 | f3 |
|---|---|---|---|
| 800m | 4.305 | 0.3045 | 0.2224 |
| 1500m | 4.964 | 0.0798 | 0.3263 |
| Mile | 5.049 | 0.0806 | 0.3092 |
| 5km | 6.179 | -0.1597 | 0.3157 |
| 10km | 6.844 | -0.1983 | 0.2717 |
| Half Marathon | 7.555 | -0.2279 | -0.1153 |
| Marathon | 8.243 | -0.2785 | -0.6912 |

**Prediction accuracy**: 2% rel.MAE for elite runners (3.6 min on Marathon, 0.3 sec on 100m).

## PIRX-Specific Implementation Notes

### Dynamic Exponent

PIRX should NOT use the fixed 1.06 exponent. Instead:

- **Aerobic-dominant runners** → higher exponent (better at longer distances relative to short)
- **Threshold-dominant runners** → lower exponent (speed holds better at shorter distances)
- Derive from the runner's `Structural Identity` in "What We're Learning About You"

### Scaling Accuracy by Distance Ratio

Cross-distance prediction is most accurate for adjacent distances:
- 1500m → 3000m: Very accurate (similar physiological demands)
- 3000m → 5K: Very accurate
- 5K → 10K: Accurate
- 3000m → Marathon: Less accurate (different energy systems)

### Modified Riegel (for experienced runners)

From Dash (2024), modified Riegel adjusts based on weekly mileage:

```
T2 = T1 × (D2 / D1) ^ (1.06 × k_marathon)
```

Where `k_marathon` is derived from the runner's typical weekly training volume. Higher mileage runners have a lower effective exponent (better endurance scaling).

## Athens Marathon Prediction Equation

Nikolaidis et al. (2021) validated on 130 runners (R² = 0.61):

```
Race Speed (km/h) = 8.804 + (0.111 × VO2max) + (0.029 × weekly_km) - (0.218 × BMI)
```

**Key correlations with marathon race speed:**
- VO2max: r = 0.67 (strongest predictor, ~40% variance)
- Weekly training distance: r = 0.58
- Body fat %: r = -0.65
- BMI: r = -0.60

**PIRX relevance**: Use weekly_km and training density as proxy inputs for event scaling where VO2max is unavailable (most consumer users). Volume-based calibration can modulate the cross-distance exponent.

## LSTM-Based Generalized Prediction

Dash (2024) achieved 90.4% accuracy across marathon to ultra distances using LSTM on running logs:

**Input features per run:**
- Distance (km)
- Elevation gain (m)
- Total time (minutes)
- Age of runner

**Key insight**: The regression approach (89.13%) outperformed time-series regression (85.21%), meaning treating each run independently is more predictive than sequential modeling for distance scaling.

**Data cleaning critical**: Removing mislabeled activities improved model performance by 12%.

## Phase Transitions in Event Scaling

Blythe & Király discovered that correlation between short-distance and long-distance performance **reverses** at key boundaries:

- **Below 5000m**: Better short-distance performance predicts *worse* long-distance performance (holding event constant)
- **Above 5000m**: This reverses — speed and endurance become positively correlated

Also, ~800m marks a qualitative physiological transition (anaerobic → aerobic dominance).

**PIRX must handle these boundaries explicitly**: event scaling models should use different logic for sub-5K vs 5K+ predictions.

## Population Norms for Individual Exponents

From Blythe & Király (164,746 runners):
- `λ1` median: **1.12** (higher than Riegel's 1.06 world-record constant)
- `λ1` 5th percentile: **1.10** (most endurance-gifted)
- `λ1` 95th percentile: **1.15** (least endurance-efficient)

Use these bounds to validate PIRX exponent estimates and flag outliers.

## Environmental Adjustment

From Grivas & Safari (2025), decision tree models on 1,258 races:
- Optimal temperature: **10–17.5°C**
- Performance decline: **0.3–0.4% per °C** outside optimal band
- R² = 0.21–0.58 depending on distance

PIRX should apply a temperature modifier to Projected Time for race-day projections.

## Non-Gaussian Distribution Handling

From Dash (2024): Running data is NOT normally distributed. Do NOT normalize training distributions when predicting performance — the long tail (high-intensity and long-distance sessions) contains critical signal. Standard normalization destroys this.

## Integration with PIRX Projection Engine

1. **Baseline race** provides T1 and D1
2. **Individual exponent** derived from training profile (aerobic vs threshold dominance)
3. **Volume modifier** adjusts exponent based on weekly training distance
4. Scale projection across all PIRX event distances
5. Supported Range width should increase for distances further from the baseline event
6. Apply **phase transition rules** at 800m and 5000m boundaries
7. Bound exponent estimates using population norms (1.10–1.15)
8. Apply **environmental correction** for race-day temperature
