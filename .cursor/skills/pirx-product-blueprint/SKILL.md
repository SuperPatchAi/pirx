---
name: pirx-product-blueprint
description: Authoritative product blueprint for the PIRX (Performance Intelligence Rx) running performance app. Enforces locked terminology, projection-first architecture, module boundaries, driver attribution rules, and UX principles. Use when building any PIRX feature, component, screen, API endpoint, data model, or test — or when making any product decision about the PIRX app.
---

# PIRX Product Blueprint

## What PIRX Is

PIRX (Performance Intelligence Rx) is a **projection-driven structural performance modeling system** for competitive runners. It answers one question: **"What does your training structurally support right now?"**

It is NOT a coach, NOT a fitness tracker, NOT a gamified health app. It behaves like a financial risk model applied to athletic performance.

## Central State Variable

**Projected Time** is the single anchor of the entire app. Every screen, module, and interaction orbits around it.

- Model-derived estimate of what the athlete can run today for a specific event
- Expressed in time format only (e.g., `9:53`)
- Updates only when structural change >= 2 seconds
- Anchored to a real Baseline Race, not VO2 estimates

## Locked Terminology (MUST follow everywhere)

| Term | Definition | Rules |
|---|---|---|
| **Projected Time** | Model-derived race estimate | Never "midpoint", "prediction score", "current capacity" |
| **Supported Range** | Performance band around Projected Time | Never "confidence interval", "variance band" |
| **Improvement Since Baseline** | Seconds diff vs Baseline Race | Always "X seconds faster/slower" |
| **21-Day Change** | Seconds diff vs projection 21 days ago | Always "X seconds faster/slower" |
| **Baseline Race** | Anchor race (manual or auto-detected) | Must show event, time, date |

### Banned Words (never in user-facing content)

Midpoint, Structural Shift, Projection Delta, Model Output, Confidence Interval, Algorithmic Adjustment, Form Score, Capacity Index

### Required Language

- Always use: **Seconds, Time, Faster, Slower**
- Never percentages for performance change on primary screens
- Projection updates: "Projection Adjusted" or "Model Updated Based on Recent Race"
- Never: "New prediction generated", "Algorithm recalculated"

## 5 Structural Drivers

Drivers MUST sum to total improvement. Always expressed in seconds.

| Driver | What It Measures |
|---|---|
| **Aerobic Base** | Z2 volume stability, 21-day volume relative to baseline |
| **Threshold Density** | Z4 minutes/week, pace near LT2 band |
| **Speed Exposure** | Z5 time, short interval frequency |
| **Load Consistency** | Weekly variance, session distribution smoothness |
| **Running Economy** | Matched HR band pace difference vs baseline |

## 12 Product Modules

| # | Module | Core Question | Modifies Projection? |
|---|---|---|---|
| 1 | **Fitness Snapshot** | What can I run today? | Source of projection |
| 2 | **Fitness Trend** | Is my structure improving? | No |
| 3 | **Driver Contribution** | What made me faster? | No (displays drivers) |
| 4 | **Two-Week Trajectory** | Where am I heading? | No (simulation only) |
| 5 | **Zone Pace Guide** | Are zones aligned? | No |
| 6 | **Running Economy** | Am I faster at same HR? | No |
| 7 | **Event Readiness** | Am I race-ready for this event? | No (0-100 score) |
| 8 | **Physiology Log** | What's happening internally? | No (v1) |
| 9 | **What We're Learning About You** | What pattern works best? | No |
| 10 | **Adjunct Analysis** | Do adjuncts correlate with change? | **Never** |
| 11 | **Current Honest State** | Narrative summary | No |
| 12 | **Mindset Check-In** | Optional subjective ratings | No |

**Critical rule**: Nothing modifies projection except the projection engine itself.

## App Navigation

Bottom tab bar with 4 tabs:

1. **Home** — Primary event tile, horizontal event swipe, driver strip, quick metrics
2. **Performance** — Full snapshot table, trajectory, readiness, adjunct analysis
3. **Physiology** — HR/HRV trends, manual blood work entry, mindset check-in
4. **Settings** — Wearable sync (Garmin/COROS/Strava), baseline selection, notifications

## Home Screen Hierarchy (top to bottom)

1. **Primary Event Tile** — Projected Time (largest element), Supported Range, Improvement Since Baseline, 21-Day Change
2. **Horizontal Event Swipe** — 1500m, 3000m, 5K, 10K
3. **Driver Strip** — Horizontal scroll, seconds per driver with 21-day arrow
4. **Quick Metrics** — Event Readiness, Running Economy Gain, Z2 Efficiency, Volatility
5. **Current Honest State** — Collapsible, calm narrative tone

## UX Design Principles

- **Dark theme dominant**
- One primary metric per screen
- Numbers first, explanations secondary
- Seconds over percentages (no % on primary screens)
- Animation only when projection changes >= 2 seconds
- Gains: subtle green accent. Losses: neutral tone (never red)
- Projection tile is brightest; secondary tiles slightly muted
- No screen exceeds 3 scroll lengths
- No daily flickering or micro-adjustments
- Calm confidence tone throughout

## Projection Update Rules

- Recalculates after every synced activity
- Visible change only if delta >= 2 seconds
- Race sync triggers immediate recalibration
- No activity >= 10 days: volatility widens, readiness decreases
- Notifications only when: projection shifts >= 2 sec, readiness shifts >= 5 pts, or adjunct reaches emerging threshold

## Projection Animation Labels

| Change | Label |
|---|---|
| 2-4 sec | Minor Update |
| 5-10 sec | Strong Session Impact |
| >10 sec | Major Performance Shift |
| Race sync | Race Integrated — Model Recalibrated |

## Event Readiness Bands

| Score | Band |
|---|---|
| 95-100 | Race Ready |
| 88-94 | Sharpening |
| 75-87 | Building |
| 60-74 | Foundational |

## Adjunct Rules (Critical)

- Adjuncts **never** modify projection
- Tracked observationally only
- Status labels: **Observational**, **Emerging**, **Supported**
- Never use: "Proven", "Effective", "Validated"
- Requires minimum session sample size

## Data Sources

- Wearable sync via OAuth: **Garmin**, **COROS**, **Strava**
- Onboarding pulls 6-12 months history
- Physiology: auto (HR, HRV, Sleep) + manual (blood lactate, blood work panels)
- Manual blood work does NOT alter projection in v1

## Non-Interference Rules

When building any module, these rules are absolute:

1. Only the projection engine writes to projection state
2. Drivers must sum to total improvement — no rounding errors allowed
3. Adjunct analysis runs parallel — never feeds back into projection
4. Physiology log is observational in v1
5. Readiness score is independent from projection (does not modify it)
6. Mindset check-in is correlation-layer only
7. Pattern detection ("What We're Learning About You") is never coaching

## Additional Resources

- For detailed technical specs (data schema, engine formulas, API contracts, feature engineering, strategic gaps), see [reference.md](reference.md)
