---
name: fatigue-readiness-classification
description: Deep learning and ML frameworks for classifying runner fatigue stages and predicting readiness from wearable sensor data. Covers CNN, LSTM, attention-based models, IMU-based fatigue detection, HRV-based recovery assessment, and stamina modeling. Use when implementing PIRX Event Readiness scoring, volatility detection, structural decay, or physiological monitoring features.
---

# Fatigue & Readiness Classification

## PIRX Application

PIRX's Event Readiness score (0-100), volatility detection, and structural decay logic require validated approaches to fatigue and readiness assessment. This skill provides the research-backed models.

## Three-Stage Fatigue Classification (Chang et al. 2023)

**Source**: 19 runners, multi-IMU outdoor running protocol.

### Fatigue Stages

| Stage | Definition | PIRX Mapping |
|---|---|---|
| **Pre-fatigue** | First 2km at steady pace | Normal training state |
| **Mid-fatigue** | Next 2km at steady pace | Moderate load accumulation |
| **Post-fatigue** | 1.2km after acceleration intervention | Structural capacity under stress |

### Best Performing Models (from raw IMU time-series)

| Model | Accuracy | Architecture |
|---|---|---|
| CNN + LSTM hybrid | **Best overall** | CNN extracts spatial features → LSTM captures temporal dependencies |
| LSTM + Attention | Strong | Attention improves processing efficiency on raw data |
| Dual-layer LSTM | Good | Sequential stacking captures deeper patterns |
| Single CNN | Good | Retains signal correlation in time-series |
| Single LSTM | Baseline | Standard recurrent approach |

### Input Data Format

```
x = [ACC(t), GYR(t), POS(t)]
```

- ACC: tri-axis acceleration (ax, ay, az)
- GYR: tri-axis angular velocity (gx, gy, gz)
- POS: tri-axis attitude angle (px, py, pz)

Window: 200 samples (1 second at 200Hz), covering ≥1 complete gait cycle.

50% overlap sliding window doubles dataset size and improves model performance.

### Peak Accuracy: 99.62% (LSTM+CNN with All Sensors)

The best configuration achieved **99.62% accuracy** on 3-stage classification using:
- All 9 input channels (ACC + GYR + POS/Euler angles)
- 50% overlap sliding window
- Lower limb sensor placement

**Critical finding**: Adding **position/Euler angles** (POS) to acceleration + gyroscope boosted accuracy from ~93% to 99%+. POS is the breakthrough feature.

**Sensor placement**: Lower limb sensor dramatically outperforms pelvis-only placement.

### RPE-to-HR Calibration Reference

When IMU data is unavailable, use HR and RPE as fatigue proxies:

| Stage | RPE (mean) | HR (mean bpm) |
|---|---|---|
| Pre-fatigue | 6.6 | 163 |
| Mid-fatigue | 11.9 | 172 |
| Post-fatigue | 15.2 | 178 |

### Key Architecture Parameters

```
LSTM hidden units: 128
Input shape: (200, input_dim)
Dropout: 0.5
L2 regularization: 0.01
Max epochs: 200
Batch size: 256
Early stopping: 14 epochs without loss reduction
```

## AI-Assisted Fatigue & Stamina Control (Biró et al. 2024)

**Source**: 19 athletes, IMU-based multivariate time series.

### Fatigue Prediction Algorithm

Combined deep learning + ensemble method:

1. **CNN layers** extract spatial features from IMU data
2. **LSTM/GRU layers** capture temporal dependencies
3. **Ensemble methods** (gradient boosting, bagging, additional NNs) predict fatigue and stamina

### Stamina Capacity Modeling

```
Stamina(t) = f(baseline_profile, recent_load, recovery_state, environmental_factors)
```

Track how long an athlete can maintain a given intensity before fatigue onset. Changes across training blocks indicate structural adaptation.

### Bias Correction (important for PIRX)

```python
B_stamina = (1/N) × Σ(predicted_stamina - true_stamina)
B_fatigue = (1/N) × Σ(predicted_fatigue - true_fatigue)

corrected_stamina = predicted_stamina - B_stamina
corrected_fatigue = predicted_fatigue - B_fatigue
```

Re-evaluate after correction to ensure bias is minimized. This aligns with PIRX's principle of projection resisting noise — systematic bias correction prevents drift.

### Fatigue Profiling & Benchmarking

1. Establish **baseline performance profile** when athlete is non-fatigued
2. Continuously compare subsequent sessions against baseline
3. Deviations indicate fatigue accumulation

**PIRX application**: This is the mechanism behind PIRX's volatility detection. When running economy or pace-at-HR deviates from baseline profile, volatility score increases.

## HRV-Based Recovery & Readiness (Grivas & Safari 2025)

### Recovery Classification from Wearables

- **Random forest classifiers** on IMU-derived biomechanical features distinguish fatigue levels
- Accuracy: 0.761 (single sensor) to 0.905 (all sensors)
- **Leave-one-subject-out validation** ensures generalizability

### HRV as Readiness Indicator

- ML models using HRV + training load + sleep + diet + wellness predict next-morning perceived recovery
- HRV used as primary autonomic nervous system marker
- Combined with training load for individualized readiness scores

**PIRX application**: Maps directly to Event Readiness calculation:

```
Readiness = weighted composite of:
  - Structural alignment score (from driver model)
  - Specificity score (from training distribution vs event demands)
  - Volatility modifier (from fatigue/recovery state)
  - Durability factor (from sustained load tolerance)
```

## Injury Risk Prediction (Raju et al. 2026)

### SHAP-Based Feature Importance for Injury

Top injury predictors via explainable AI:
1. **ACL risk score** (biomechanical)
2. **Load balance score** (training load vs recovery)
3. **Fatigue score** (accumulated fatigue)
4. **Training hours** (volume)

**Random Forest** performed best: accuracy = 0.98, ROC-AUC = 0.97.

**PIRX application**: Load balance and fatigue scores directly inform PIRX's:
- Volatility widening logic (high fatigue → wider Supported Range)
- Structural decay detection (>10 days no activity)
- Risk Pattern in "What We're Learning About You"

### SHAP Directional Feature Importance (Raju et al. 2026)

| Feature | SHAP Importance | Direction |
|---|---|---|
| ACL Risk Score | 0.394 | ↑ score → ↑ injury risk |
| Load Balance Score | 0.218 | ↑ balance → ↓ injury risk |
| Fatigue Score | 0.072 | ↑ fatigue → ↑ injury risk |
| Training Hours | 0.068 | ↑ hours → ↑ risk (overtraining) |

**PIRX application**: Use SHAP-style directional arrows in Driver Contribution to explain "why did this driver change?"

## Iterative Bias Correction Loop (Biró et al. 2024)

For production projection systems, apply iterative bias correction with convergence:

```python
epsilon = 0.01  # convergence threshold
while True:
    bias = mean(predicted - actual)  # across recent projections
    corrected = predicted - bias
    new_error = mean(abs(corrected - actual))
    if abs(new_error - prev_error) < epsilon:
        break
    prev_error = new_error
```

This prevents systematic drift in PIRX projections over time.

## Injury Risk as Continuous Probability (Smyth et al. 2022)

Binary injury prediction fails (precision < 0.1 for 14-day disruptions). Instead:
- Use Random Forest **positive-class probability** as continuous risk score
- This probability correlates with actual injury incidence at **Spearman > 0.9**
- Maps perfectly to Event Readiness score decay (higher injury risk → lower readiness)

## Implementation for PIRX Readiness Score

Based on the studies, a practical Event Readiness implementation:

```python
def compute_readiness(event, driver_state, training_profile, physiology):
    structural_alignment = compute_alignment(event, driver_state)
    specificity = compute_specificity(event, training_profile)
    volatility_mod = 1.0 - (volatility_score * 0.3)
    durability = compute_durability(training_profile)
    
    raw_score = (
        0.35 * structural_alignment +
        0.30 * specificity +
        0.20 * volatility_mod +
        0.15 * durability
    )
    
    # EMA smoothing to prevent day-to-day jitter
    smoothed = alpha * raw_score + (1 - alpha) * previous_readiness
    return max(0, min(100, smoothed * 100))
```

Structural alignment checks if training distribution matches event demands:
- 3000m needs high Z4/Z5 → reward threshold density and speed exposure
- 10K needs high Z2 + Z4 → reward aerobic base and threshold density
- 1500m needs high Z5 → reward speed exposure heavily
