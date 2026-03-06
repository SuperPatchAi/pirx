---
name: local-matrix-completion
description: Local Matrix Completion (LMC) algorithm for predicting individual runner performance across distances using sparse race data. Provides the mathematical framework, three-number runner summary, and implementation guidance for PIRX performance prediction. Use when building the projection engine, implementing baseline estimation, or developing the runner profiling system.
---

# Local Matrix Completion for Runner Performance

## PIRX Application

LMC is the state-of-the-art method for predicting a runner's performance across distances from sparse race history. It directly supports PIRX's core need: predicting what a runner can run today across multiple events from limited data.

## The Method

**Source**: Blythe & Király (2016), PLOS ONE. 164,746 runners, 1,417,432 performances.

LMC assumes a small number of explanatory variables (rank `r`) describe all runner performances. It outperforms Riegel formula by 30% (RMSE) and beats Purdy Points, k-NN, and Expectation Maximization.

### Core Model

Every runner's log-time at distance `s` is modeled as:

```
log(time_s) = λ1 × f1(s) + λ2 × f2(s) + λ3 × f3(s)
```

Where:
- `f1, f2, f3` are **universal components** (same for all runners)
- `λ1, λ2, λ3` are **individual coefficients** (unique per runner)

### Three-Number Runner Summary

| Parameter | Interpretation | PIRX Mapping |
|---|---|---|
| `λ1` | Overall endurance / power law exponent | Maps to general performance level |
| `λ2` | Speed-endurance balance | Maps to aerobic vs speed dominance |
| `λ3` | Middle-distance specialization | Maps to event-specific readiness |

**Key insight**: `λ1` explains most variance for distances > 800m and corresponds to an individual power law. Runners with higher `λ1` are slower overall.

### Optimal Rank

- Rank 2 always outperforms rank 1 (p < 1e-4)
- Rank 3 outperforms rank 2 when 4+ event performances are available
- For PIRX v1 (users with 1-3 race results), rank 2 is optimal
- Rank 2 improvement over rank 1: 26% for sprints, 29% for middle distances, 31% for endurance

## Prediction Accuracy

| Method | RMSE (log-time) | vs LMC rank 2 |
|---|---|---|
| Riegel formula | 0.0982 | 47% worse |
| Power law (individual) | 0.1033 | 50% worse |
| k-NN | 0.0618 | 17% worse |
| Purdy Points | 0.0610 | 16% worse |
| **LMC rank 2** | **0.0515** | **baseline** |

Absolute prediction errors:
- Marathon: ~3.6 minutes (elite)
- 1500m: ~3 seconds
- 100m: ~0.3 seconds

## Implementation for PIRX

### Step 1: Build the Component Matrix

Pre-compute `f1, f2, f3` from a reference population of runners. Use values from the paper or train on your own user base:

```python
F = {
    '1500m': [4.964, 0.0798, 0.3263],
    '3000m': [5.621, -0.040, 0.299],  # interpolated
    '5km':   [6.179, -0.1597, 0.3157],
    '10km':  [6.844, -0.1983, 0.2717],
}
```

### Step 2: Estimate Runner Coefficients

Given a runner's known performances (at least 1, preferably 2+):

```python
# Solve for λ given observed performances
# λ = argmin ||observed_log_times - F @ λ||^2
import numpy as np

def estimate_runner(known_events, known_times, F):
    F_sub = np.array([F[event] for event in known_events])
    log_times = np.log(known_times)
    lambda_hat = np.linalg.lstsq(F_sub, log_times, rcond=None)[0]
    return lambda_hat
```

### Step 3: Predict Across Events

```python
def predict_time(lambda_hat, target_event, F):
    f_target = np.array(F[target_event])
    log_time_pred = np.dot(lambda_hat, f_target)
    return np.exp(log_time_pred)
```

### Cold Start (No Race Data)

When a runner has no race results, use sustained high-intensity efforts as proxy:
1. Identify longest continuous threshold-pace segments
2. Estimate equivalent race time using effort-to-race conversion
3. Apply LMC with reduced confidence

This aligns with PIRX's edge case: "System auto-estimates baseline from sustained efforts."

### Updating with New Races

When a new race result arrives:
1. Add to known performances
2. Re-estimate `λ1, λ2, λ3`
3. Recompute all event projections
4. Apply PIRX smoothing (change >= 2 sec threshold)

## Physiological Interpretation

The three parameters relate to real physiology:

- **`λ1` tracks training state**: Improves with consistent training, decays with inactivity
- **`λ2` tracks specialization**: Shifts based on training zone emphasis (Z2 heavy → endurance; Z5 heavy → speed)
- **`λ3` tracks event-specific fitness**: Sensitive to block periodization

This maps cleanly to PIRX's driver model:
- Aerobic Base / Load Consistency → primarily affect `λ1`
- Speed Exposure / Threshold Density → primarily affect `λ2`
- Running Economy → affects all three via efficiency gains

## Population Statistics for λ Values

From Blythe & Király (164,746 runners):

| Statistic | λ1 |
|---|---|
| Median | 1.12 |
| 5th percentile | 1.10 |
| 95th percentile | 1.15 |

**Elite reference values:**

| Runner | λ1 | λ2 | λ3 | Specialization |
|---|---|---|---|---|
| Mo Farah | 1.08 | 0.033 | -0.076 | Middle-Long |
| Gebrselassie | 1.08 | 0.114 | -0.056 | Long |
| Seb Coe | 1.09 | -0.085 | -0.036 | Middle |
| Usain Bolt | 1.11 | -0.367 | 0.081 | Sprint |

Use these for calibration anchors and to contextualize PIRX user profiles.

## Standard Errors on Components

The component values have known uncertainty:
- `v` (raw singular vector) entries: ±0.005
- `f2` entries: ±0.02
- `f3` entries: ±0.04

PIRX should propagate these uncertainties into the Supported Range width calculation — larger uncertainty at the component level → wider Supported Range.

## The LMC Algorithm Detail

For prediction, LMC uses the determinant condition on sub-pattern matrices:

For a rank-r model, take any (r+1)×(r+1) sub-matrix A of the runner-event matrix. If one entry "?" is unknown:

```
det(A) = 0  →  solve for "?"
```

Multiple such sub-patterns exist; the algorithm averages predictions across all valid patterns to minimize expected error. This is more robust than simple least-squares when data is very sparse (1-2 known performances).

## Rank 2 Improvement Varies by Distance

| Target Distance Group | Rank 2 improvement over Rank 1 |
|---|---|
| Short (100m, 200m) | 26.3% |
| Middle (400m, 800m, 1500m) | 29.3% |
| Mile to Half-Marathon | 12.8% |
| Marathon | 3.1% |

PIRX should adjust projection confidence by target event: middle-distance projections benefit most from rank 2, while marathon projections are nearly as good with rank 1.

## Key Takeaway for PIRX

LMC provides the most accurate performance prediction from sparse data. A runner needs only 1-2 race results to produce projections across all events. The three-number summary creates a compact, interpretable runner profile that can be tracked over time as a structural fitness indicator.
