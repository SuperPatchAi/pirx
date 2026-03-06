---
name: race-time-prediction-ml
description: Machine learning approaches for predicting race times from training data, including KNN, ANN, case-based reasoning, gradient boosting, and recommender systems for runners. Provides model architectures, input features, accuracy benchmarks, and implementation patterns for PIRX projection engine. Use when building or improving the projection model, implementing finish-time estimation, or developing pacing recommendations.
---

# Race Time Prediction with ML

## PIRX Application

PIRX's Projected Time is the central state variable. This skill provides the ML models, feature sets, and accuracy benchmarks for generating and validating that projection.

## KNN vs ANN for Race Prediction (Lerebourg et al. 2023)

**Source**: 820 athletes, French Athletics Federation official rankings.

### Input Features

```
Inputs: [10km_time, BMI, age, sex]
Output: Marathon_time (minutes)
```

### KNN Implementation (k=3)

```python
def predict_knn(athlete, training_set, k=3):
    distances = [euclidean(athlete.features, t.features) for t in training_set]
    nearest_k = sorted(zip(distances, training_set))[:k]
    weights = [1/d for d, _ in nearest_k]
    predicted = sum(w * t.marathon_time for w, (_, t) in zip(weights, nearest_k))
    return predicted / sum(weights)
```

### ANN Architecture

```
Input layer: [10km_time, BMI, age, sex] (normalized)
Hidden layer: 2 neurons, sigmoid activation
Output layer: 1 neuron (marathon time)
```

ANN equation (from the paper, directly implementable):

```
Marathon_time = (((1/(1+exp(-((norm_10k * 0.1717) + (norm_BMI * -1.11518) 
  + (norm_age * 0.28333) + (norm_sex * 0.95911) + 0.68255)))) * -1.5208) 
  + ((1/(1+exp(-((norm_10k * -0.78176) + (norm_BMI * 0.21688) 
  + (norm_age * -0.05194) + (norm_sex * -0.30595) + -0.06117)))) * -4.98486) 
  + 3.41225) * 37.77 + 204.84
```

### Performance Comparison

| Model | MAE | Correlation | Bias |
|---|---|---|---|
| **KNN (k=3)** | **2.4%** (4 min 48s) | r = 0.982 | -47 sec |
| ANN | 5.6% (11 min 16s) | r = 0.918 | +3 min 14s |

**Key finding**: KNN outperforms ANN on this task. KNN is simpler, less prone to overfitting, and provides built-in explainability ("your projection is based on runners similar to you").

**PIRX relevance**: KNN's "similar runners" approach aligns with PIRX's structural modeling philosophy — find structurally similar athletes and learn from their patterns.

## Case-Based Reasoning for Race Prediction (Smyth et al. 2022)

**Source**: University College Dublin, multi-year marathon race data.

### The CBR Approach

```
case(r, mi, mj) = (nPB(r, mi), PB(r, mj))
```

Where:
- `r` = runner
- `mi, mj` = two different races
- `nPB` = non-personal-best time
- `PB` = personal best time

**Process:**
1. Build case database from historical runner data
2. Query with a runner's recent (non-PB) race result
3. Retrieve k most similar cases
4. Average their PB times to predict the runner's potential

### Fitness Estimation from Training Data

Uses cumulative training load features:

```python
fitness_features = {
    'weekly_distance': rolling_sum(distances, 7),
    'weekly_duration': rolling_sum(durations, 7),
    'long_run_distance': max(week_distances),
    'avg_pace': mean(session_paces),
    'pace_variability': std(session_paces),
    'session_count': count(sessions_per_week),
    'rest_days': count(rest_days_per_week),
}
```

### Training Plan Recommendation

CBR also generates personalized training plans:
1. Match runner to similar runners who achieved target time
2. Extract their training patterns
3. Adapt plan to runner's schedule and preferences

**PIRX application**: This supports "What We're Learning About You" — finding structural patterns from similar runners.

## LSTM for Generalized Prediction (Dash 2024)

### Architecture

```
Input sequence → LSTM layers → Fully Connected → Predicted time
```

**Input features per run:**
- Distance (km)
- Elevation gain (m)
- Total time (minutes)
- Age (years)

### Regression vs Time Series

| Approach | Accuracy |
|---|---|
| **Regression** (each run independent) | **89.13%** |
| Time Series Regression | 85.21% |

Regression outperforms TSR because running logs have:
- Missing data (rest days)
- Variable paces for same distances (easy runs vs tempo vs race)
- Low Pearson correlation between sequential runs (r = 0.221)

### Comparison to Benchmarks

| Model | Accuracy (60 races) |
|---|---|
| **LSTM (regression)** | **90.4%** |
| UltraSignup formula | 87.5% |
| Riegel formula | 80.0% |

### Data Cleaning Algorithm (Critical)

Improved model performance by 12%:

1. Filter: activity_type == "run" only
2. Remove: missing data, zero elevation, zero moving time
3. Remove: activities < 3 minutes
4. Remove: runs < 1.6 km
5. Remove: pace slower than runner's average (likely mislabeled walks)
6. Remove: pace faster than world record mile (3:43) — likely bike/ski data

**PIRX application**: Apply this cleaning pipeline to all ingested wearable data before feature engineering.

## Gradient Boosting for Performance Prediction (Qin et al. 2025)

### Model Architecture

Hybrid approach:
- **Gradient Boosting Regression** → performance prediction
- **SVM Classification** → training zone assignment

### Weighted Training Load Formula

```
P(t) = f(Σ(i=1 to n) wi × TLi(t) × e^(-λ(t-ti)))
```

Exponential decay ensures recent training has more influence.

### Hyperparameters (validated)

| Parameter | Value |
|---|---|
| Learning rate | 0.0075-0.0092 |
| Epochs | 250-275 |
| Batch size | 64 |
| Dropout | 0.35-0.40 |
| L2 regularization | 0.0018-0.0025 |
| Optimizer | Adam |

### 27 Engineered Features

Across 5 domains:
1. **Cardiovascular**: HR, HRV, HR zones, recovery HR
2. **Movement/GPS**: distance, pace, elevation
3. **Training load**: session duration, weekly totals
4. **Subjective**: RPE, fatigue, sleep quality
5. **Performance testing**: time trials, VO2max

## Accuracy Targets for PIRX

Based on the literature, PIRX should aim for:

| Metric | Target | Source |
|---|---|---|
| Projection accuracy (primary event) | ±7 seconds (stated benchmark) | PIRX spec |
| Cross-distance scaling | MAE < 3% | Blythe & Király |
| Training response prediction | Direction correct >66% | Zrenner et al. |
| 21-day change detection | > 2 sec threshold | PIRX spec |

## Critical Speed & Functional Threshold Pace (Smyth et al. 2022)

From 1.86M Strava activities across 31K runners:

### Fitness Models from GPS Data Alone (No Lab Required)

| Model | What It Measures | How to Compute |
|---|---|---|
| **Fastest Pace** | Cumulative fastest paces at 1500m, 5K, 10K, 30K | Max pace over rolling segments |
| **Functional Threshold Pace (FTP)** | Sustainable threshold intensity | Best 20-min pace × 0.95 |
| **VO2max (Daniels-Gilbert)** | Aerobic capacity estimate | From race/TT performances |
| **Critical Speed + D'** | Sustainable race pace + speed reserve | From multiple time-to-exhaustion efforts |

Combined model predicts marathon time within **14.34 minutes (<6% error)** using Gradient Boosting.

### Daniels-Gilbert VO2max Formula

```
VO2max = (-4.60 + 0.182258×v + 0.000104×v²) / (0.8 + 0.1894393×e^(-0.012778×t) + 0.2989558×e^(-0.1932605×t))
```

Where `v` = velocity (m/min), `t` = time (minutes). Apply to cumulative fastest training paces at each distance.

**PIRX application**: Use internally for fitness indexing without ever showing "VO2max" to users.

## Huber Loss for Robust Prediction (Dash 2024)

PIRX should use **Huber loss** instead of MSE for all time-prediction models:

```python
def huber_loss(y_true, y_pred, delta=1.0):
    error = y_true - y_pred
    return np.where(abs(error) <= delta,
                    0.5 * error**2,
                    delta * (abs(error) - 0.5 * delta))
```

Huber loss is robust to outliers (bad GPS data, anomalous sessions) that are inherent in running logs.

## Bland-Altman Validation Standard (Lerebourg et al. 2023)

PIRX should validate projections using Bland-Altman analysis, not just MAE:

```
Bias = mean(actual - predicted)
95% LoA = Bias ± 1.96 × SD(actual - predicted)
```

**Acceptance criteria from the literature:**
- MAE < 5% for model validity
- Effect size (Cohen's d) ≤ 0.1 for trivial bias
- 95% LoA within acceptable clinical range

## BMI as #2 Predictor (Lerebourg et al. 2023)

BMI has the **strongest negative weight** (-1.115) in the validated ANN equation — second only to 10km time. PIRX onboarding should collect height and weight. Previously finished race count is NOT predictive (r = 0.08).

## Pacing Strategy from CBR (Smyth et al. 2022)

Race pacing profiles can be predicted using cosine similarity on relative split data:

1. Encode each runner's race as a vector of relative split paces
2. Find k most similar historical race profiles (cosine distance)
3. Average their pacing strategies → recommended pacing plan
4. Achieves ~5% average error

**PIRX application**: Powers the Two-Week Trajectory module and race-day pacing recommendations.

## Per-Runner Model Personalization (Dash 2024)

Each runner should get their own model with unique hyperparameters — not a single global model. 15 individual LSTM networks outperformed a single global network. This validates PIRX's individual Structural Identity concept.

## LSTM Architecture (Exact — Dash 2024)

| Parameter | Value |
|---|---|
| Neurons | 17 |
| Sequence length | 11 |
| Batch size | 56 |
| Learning rate | 0.018468 |
| Dropout | 50% |
| Loss | **Huber** |
| Optimizer | Adam |
| HPO | Optuna, 60 trials |
| Framework | PyTorch |

## Recommended Model Stack for PIRX v1

1. **LMC rank 2** for cross-distance projection from race data
2. **KNN (k=3, weighted)** for finding structurally similar runners (r² = 0.964)
3. **Gradient Boosting** for driver-to-projection regression
4. **EWMA smoothing** for volatility control
5. **Exponential decay weighting** for rolling window (0.45/0.35/0.20 as specified)
6. **Huber loss** for all regression training (robust to outliers)
7. **Bland-Altman** for all validation (bias ± 95% LoA)
8. **Critical Speed + D'** for threshold pace estimation from GPS data
