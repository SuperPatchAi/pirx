# PIRX Product Requirements Document (Lightweight)

> Version 1.0 | March 2026
> Companion to: `PIRX_Architecture_Reference.md`, Feature Breakdown Plan, `.cursor/skills/pirx-product-blueprint/`

---

## Purpose

This document adds **priority tiers** and **acceptance criteria** to the PIRX feature set defined in the Feature Breakdown Plan. It does not duplicate feature descriptions — refer to the Feature Breakdown Plan for full specs, architecture mappings, and skill references.

---

## Priority Definitions

| Tier | Meaning | Phase |
|------|---------|-------|
| **P0** | Launch blocker. App cannot ship without this. | Phase 1 (Weeks 1-8) |
| **P1** | Core intelligence. Required for product differentiation. | Phase 2 (Weeks 9-16) |
| **P2** | AI-native features. Required for full product vision. | Phase 3 (Weeks 17-24) |
| **P3** | Growth and scale features. Post-launch. | Phase 4 (Weeks 25-32) |

---

## Success Metrics (KPIs)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Onboarding completion rate | > 70% | Users who reach first projection / total signups |
| Time to first projection | < 5 minutes | From signup to projection display (excluding backfill) |
| Projection accuracy | MAE < 5% | Bland-Altman: Cohen's d <= 0.1 |
| Daily active users returning to Home | > 40% DAU/MAU | Analytics |
| Chat engagement | > 30% of users use chat weekly | Message count per active user |
| Wearable sync success rate | > 95% | Successful syncs / total sync attempts per provider |
| Push notification open rate | > 25% | Opens / delivered |

---

## Feature 1: Onboarding Flow — P0

### Acceptance Criteria

- [ ] User can create account via email/password, magic link, Google, or Apple Sign-In
- [ ] User can connect at least one wearable (Garmin or Strava) via OAuth
- [ ] Terra widget renders and completes OAuth flow without errors on mobile Safari and Chrome
- [ ] Historical data pull retrieves 6-12 months of activity data within 5 minutes
- [ ] Progress indicator accurately reflects backfill Celery task progress
- [ ] System auto-detects best race effort from history; if no race found, falls back to sustained-effort LMC cold start
- [ ] User can manually override baseline race selection
- [ ] User can select primary event (1500m, 3000m, 5K, 10K)
- [ ] First projection is generated and displayed with animation upon event selection
- [ ] Supported Range is shown alongside Projected Time
- [ ] All 5 driver states are initialized
- [ ] `Projection_State` and `Driver_State` rows exist in database after onboarding
- [ ] RLS policies prevent cross-user data access from the moment of account creation

### Edge Cases

- No race data found -> sustained-effort proxy with "Estimated" label and wider Supported Range
- Wearable connection fails -> retry button + option to skip and connect later
- Backfill returns 0 valid activities after cleaning -> error state with manual entry prompt
- User abandons mid-flow -> state persisted, can resume

---

## Feature 2: Home Tab — P0

### Acceptance Criteria

- [ ] Projected Time renders as the largest element on screen in `mm:ss` format
- [ ] Supported Range displays below Projected Time
- [ ] Improvement Since Baseline shown in seconds ("X seconds faster")
- [ ] 21-Day Change shown in seconds
- [ ] Status label reflects current state: Holding / Improving / Projection Adjusted / Updated Based on Recent Race
- [ ] Projection animates ONLY when change >= 2 seconds; silent otherwise
- [ ] Horizontal event swipe shows all 4 events (1500m, 3000m, 5K, 10K) with Projected Time per event
- [ ] Swiping changes the top tile live
- [ ] Tapping an event card navigates to Event Detail
- [ ] Driver Strip shows 5 drivers with contribution in seconds (negative = improvement)
- [ ] Tapping a driver navigates to Driver Detail
- [ ] Driver values sum to total improvement (no rounding errors visible)
- [ ] Quick Metrics show Event Readiness score, Running Economy Gain, Volatility Status
- [ ] Sync Banner appears when new activity is detected: "New Activity Synced" or "Projection Adjusted"
- [ ] Race sync triggers: "Model Updated Based on Recent Race"
- [ ] Supabase Realtime subscription updates projection tile within 2 seconds of backend change
- [ ] Dark theme renders correctly with proper contrast ratios (WCAG AA)

### Edge Cases

- No projection yet (new user, backfill in progress) -> skeleton loader with "Calculating..." state
- Stale projection (>10 days no activity) -> "No Recent Data" badge, widened Supported Range
- All drivers at zero (no change from baseline) -> show "0s" per driver, total improvement "0 seconds"

---

## Feature 3: Event Detail Screen — P0

### Acceptance Criteria

- [ ] Projected Time displayed large at top with Supported Range and confidence level
- [ ] 90-day projection history chart renders as line chart with shaded range band
- [ ] X-axis shows dates (formatted via date-fns), Y-axis shows time in `mm:ss`
- [ ] Improvement Since Baseline and 21-Day Change shown below chart
- [ ] "View Driver Breakdown" CTA navigates to Driver Contribution
- [ ] "View 2-Week Trajectory" CTA navigates to Trajectory module
- [ ] Back navigation returns to Home
- [ ] Chart loads within 1 second for 90 days of data points

---

## Feature 4: Driver Detail Screen — P0

### Acceptance Criteria

- [ ] Driver name and total contribution (seconds) shown at top
- [ ] 42-day trend line chart renders correctly
- [ ] 21-Day Change for the specific driver shown
- [ ] Stability Indicator displays: Stable / Active / Declining
- [ ] Structural explanation text describes what the driver measures
- [ ] Back navigation returns to previous screen (Event Detail or Home)

---

## Feature 5: Performance Tab — P1

### 5A. Fitness Snapshot — P0

#### Acceptance Criteria

- [ ] Table shows all 4 events with Projected Time and Supported Range
- [ ] Times stored internally as seconds, displayed as `mm:ss`
- [ ] Improvement Since Baseline and 21-Day Change shown
- [ ] Baseline Race info displayed (event, time, date)

### 5B. Fitness Trend — P1

#### Acceptance Criteria

- [ ] 90-day chart with line (midpoint) and area (range band)
- [ ] Last 21 Days and Last 90 Days deltas shown in seconds
- [ ] Volatility label: Low / Medium / High
- [ ] Trend Status: Improving / Holding / Declining

### 5C. Driver Contribution — P1

#### Acceptance Criteria

- [ ] Horizontal bar chart with all 5 drivers
- [ ] Bars sum exactly to total improvement (server-side enforced, client validates)
- [ ] Each bar tappable -> navigates to Driver Detail
- [ ] "Why?" expandable shows SHAP-style directional explanation
- [ ] SHAP explanation text uses PIRX locked terminology

### 5D. Two-Week Trajectory — P1

#### Acceptance Criteria

- [ ] 3 scenario cards: maintain, increase threshold, reduce load
- [ ] Each shows projected time for that scenario
- [ ] All values bounded to +/- 1.5% of current projection
- [ ] No forecasting language used ("If structure maintained", not "We predict")
- [ ] No ranges shown on scenario cards

### 5E. Zone Pace Guide — P1

#### Acceptance Criteria

- [ ] Zone table Z1-Z5 with pace ranges per zone
- [ ] 21-Day Distribution chart (pie or bar)
- [ ] Z2 Efficiency Gain shown in seconds per km
- [ ] Training methodology classification shown (Pyramidal / Polarized / Mixed)

### 5F. Running Economy — P1

#### Acceptance Criteria

- [ ] Matched HR Band, Baseline Pace, Current Pace, Efficiency Gain all displayed
- [ ] HR Cost Change shown in bpm
- [ ] Economy split into 3 intensity levels (Easy, Threshold, Race)
- [ ] Each level shows its own efficiency delta

### 5G. Event Readiness — P1

#### Acceptance Criteria

- [ ] Table: Event, Score (0-100), Stage label
- [ ] Stage labels: Peak Alignment (95-100), Sharpening (88-94), Building (75-87), Foundational (60-74)
- [ ] Color-coded badges per stage
- [ ] Does NOT modify projection state (enforced server-side)

### 5H. What We're Learning About You — P2

#### Acceptance Criteria

- [ ] Structural Identity label displayed (e.g., "Threshold-Dominant")
- [ ] At least 1 Repeatable Pattern shown when data supports it
- [ ] Risk Patterns displayed when detected
- [ ] Block Consistency: High / Medium / Low
- [ ] Optimal Methodology suggestion shown
- [ ] All content is observational — no coaching language
- [ ] Patterns stored as embeddings for chat RAG retrieval

### 5I. Adjunct Analysis — P1

#### Acceptance Criteria

- [ ] Dropdown to select adjunct
- [ ] Per adjunct: Sessions Analyzed, Median Projection Delta, HR Drift Change, Volatility Change
- [ ] Status escalation: Observational -> Emerging -> Supported
- [ ] Escalation based on n >= threshold, variance < threshold, consistent directionality
- [ ] Statistical confidence indicator displayed
- [ ] NEVER modifies projection (enforced server-side)
- [ ] Never uses "Proven", "Effective", or "Validated" language

### 5J. Current Honest State — P1

#### Acceptance Criteria

- [ ] "What Today Supports", "What Is Defensible", "What Needs Development" sections
- [ ] Narrative text only — no new data visualizations
- [ ] Calm, confident tone

---

## Feature 6: Physiology Tab — P1

### 6A + 6B: Trends + Manual Entry

#### Acceptance Criteria

- [ ] Resting HR, HRV, Sleep Score trend lines for 30 days
- [ ] Manual entry form: Blood Lactate (4 fields), Blood Work (8+ fields), Context Notes
- [ ] Form validates input (numeric ranges for blood values)
- [ ] Manual entries do NOT affect projection (enforced)
- [ ] Entries stored with `source = 'manual'` tag

### 6C: Mindset Check-In — P2

#### Acceptance Criteria

- [ ] Confidence, Fatigue, Focus sliders (1-10 scale)
- [ ] Free text notes field
- [ ] 30-day trend graph per metric
- [ ] Correlation-layer only — no projection impact (enforced)

---

## Feature 7: Settings Tab — P0

### Acceptance Criteria

- [ ] Connected wearables list shows provider name, status, last sync time
- [ ] "Connect" launches Terra widget or direct OAuth (Strava)
- [ ] "Disconnect" revokes tokens and removes connection
- [ ] Baseline Selection: auto-select toggle + manual race list
- [ ] Baseline change warning modal displayed before confirmation
- [ ] Baseline change recalculates "Improvement Since Baseline" only (NOT projection)
- [ ] Primary Event radio buttons: 1500m, 3000m, 5K, 10K
- [ ] Adjunct Library: list, add custom, edit, delete
- [ ] Notification toggles for all 6 trigger types (default: all on)
- [ ] Account: email display, password change, data export button, data deletion button
- [ ] Data export generates complete JSON/CSV
- [ ] Data deletion performs cascading delete with confirmation dialog
- [ ] All settings changes persist immediately via Supabase

---

## Feature 8: AI Chat — P2

### Acceptance Criteria

- [ ] Floating action button visible on all screens
- [ ] Full-screen chat interface with dark theme
- [ ] Streaming token-by-token responses visible in real-time
- [ ] Message history persisted per conversation thread
- [ ] Quick suggestion chips shown on empty chat state
- [ ] All 8 agent tools functional: `get_projection`, `get_drivers`, `get_training_history`, `get_readiness`, `get_physiology`, `search_insights`, `compare_periods`, `explain_driver`
- [ ] Agent uses locked PIRX terminology in all responses
- [ ] Agent never coaches — observes and explains only
- [ ] Banned terms trigger terminology correction in agent system prompt
- [ ] RAG retrieves relevant context from `user_embeddings` via cosine similarity
- [ ] Response latency < 3 seconds to first token
- [ ] Conversation threads isolated per user (RLS enforced)

---

## Feature 9: Notification System — P1

### Acceptance Criteria

- [ ] Push notifications delivered via PWA service worker
- [ ] 6 trigger types: Projection Update (>= 2s), Readiness Shift (>= 5 pts), Intervention Signal, Weekly Summary, Race Approaching, New Insight
- [ ] Each notification type independently toggleable
- [ ] No daily micro-alerts — all threshold-gated
- [ ] Notification tapped -> deep link to relevant screen
- [ ] Weekly summary includes: projection changes, driver shifts, training volume recap

---

## Feature 10: Social Layer — P3

### Acceptance Criteria

- [ ] Shareable Race Prediction Card with Projected Time, Range, Event Readiness
- [ ] Card formatted for Instagram Stories aspect ratio
- [ ] Cohort benchmarking shows anonymized comparison with similar runners
- [ ] Post-race share: Actual vs Projected with driver attribution

---

## Feature 11: Coach Dashboard — P3

### Acceptance Criteria

- [ ] Multi-athlete list with projection summaries per athlete
- [ ] Per-athlete drill-down: full Performance tab equivalent
- [ ] Alert feed: projection changes, readiness shifts, risk patterns across roster
- [ ] Coach can only see athletes who have granted access
- [ ] RLS enforces coach-athlete relationship at database level

---

## Cross-Cutting Requirements

### Authentication — P0

- [ ] Supabase Auth: email/password, magic link, Google, Apple Sign-In
- [ ] JWT tokens issued and validated on all API calls
- [ ] RLS enabled on all tables; users access only their own data
- [ ] Wearable OAuth tokens encrypted before storage (AES-256)

### Data Pipeline — P0

- [ ] Data cleaning pipeline filters: runs only, >= 3 min, >= 1.6 km, pace within bounds
- [ ] Feature engineering computes 27 features across 5 domains (volume, intensity, efficiency, consistency, physiological)
- [ ] Rolling windows: 7d (0.45), 8-21d (0.35), 22-90d (0.20)
- [ ] Structural shift threshold: >= 2 seconds triggers projection recompute
- [ ] All Projection_State and Driver_State writes are immutable (append-only)
- [ ] Drivers sum to total improvement — server-side validation, no rounding errors

### ML Model Accuracy — P0

- [ ] All regression models trained with Huber loss
- [ ] Bland-Altman validation: Bias +/- 95% Limits of Agreement
- [ ] Acceptance gate: MAE < 5%, Cohen's d <= 0.1
- [ ] Iterative bias correction loop with epsilon = 0.01 convergence
- [ ] Model metrics logged to `model_metrics` table

### PWA — P0

- [ ] `manifest.json`: display standalone, orientation portrait, start_url /dashboard
- [ ] Service worker: stale-while-revalidate for API data
- [ ] Offline: show last cached projection with "offline" badge
- [ ] Installable on iOS and Android via "Add to Home Screen"

### Observability — P1

- [ ] Sentry error tracking on frontend and backend
- [ ] Vercel Analytics for Core Web Vitals
- [ ] Custom FastAPI middleware logs request latency and error rates
- [ ] Celery Flower for queue monitoring
- [ ] Wearable sync success rate tracked per provider

### Data Privacy — P0

- [ ] All data encrypted at rest (AES-256) and in transit (TLS 1.3)
- [ ] GDPR: data export endpoint, data deletion endpoint with cascading delete
- [ ] PIPEDA: consent on collection, purpose limitation
- [ ] Audit log table for all data access
- [ ] No third-party analytics on raw user health data

---

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Page load (Home) | < 2 seconds (LCP) |
| API response (projection) | < 500ms (p95) |
| First token (chat) | < 3 seconds |
| Projection recompute | < 15 seconds end-to-end |
| Uptime | 99.5% |
| Concurrent users | 1,000 (Phase 1), 10,000 (Phase 3) |
| Database connections | Supabase managed pool |

---

## Phase Alignment Summary

| Phase | Timeline | P-Tier | Key Deliverables |
|-------|----------|--------|------------------|
| **Phase 1: Foundation** | Weeks 1-8 | P0 | Supabase schema + RLS, Next.js PWA scaffold, FastAPI core endpoints, Strava + Garmin integration, LMC rank 2 projection, Home tab, Event/Driver Detail, Settings, Onboarding |
| **Phase 2: Intelligence** | Weeks 9-16 | P1 | Feature engineering pipeline, KNN seeding, Driver attribution (Gradient Boosting), Event Readiness, Full Performance tab, Physiology tab, Notifications, Terra API expansion |
| **Phase 3: AI-Native** | Weeks 17-24 | P2 | LangGraph chat agent, RAG pipeline, Per-user LSTM training, SHAP explanations, What We're Learning, Mindset Check-In, iOS/Android native wrappers |
| **Phase 4: Scale** | Weeks 25-32 | P3 | Social layer, Coach Dashboard, Adjunct Analysis advanced stats, Diagnostic Lab API, CBR pacing, Model accuracy public benchmark |
