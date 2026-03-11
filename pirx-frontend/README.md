# PIRX Frontend Reference

Frontend application for PIRX built with Next.js App Router, Supabase auth/session, and backend APIs served by `pirx-backend`.

Use this as the frontend source-of-truth alongside:

- root `README.md` (end-to-end architecture, data flow, ML)
- `pirx-backend/migrations/README.md` (schema/migrations)

## Tech Stack

- Next.js App Router (`src/app`)
- React + TypeScript
- Supabase client/session (`@supabase/ssr`)
- shadcn/ui components
- Zustand stores for projection and tour state
- Framer Motion + Recharts for interaction/visualization

## Local Development

From `pirx-frontend`:

```bash
npm install
npm run dev
```

App runs on `http://localhost:3000` by default.

Required frontend env vars:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL` (backend base URL, defaults to `http://localhost:8001`)

## Frontend Architecture

### Route groups

- `src/app/(auth)` - login/signup/auth entry points
- `src/app/(app)` - authenticated app shell and core product pages
- `src/app/(public)` - public/legal/static pages
- `src/app/auth/callback/route.ts` - Supabase auth callback exchange/redirect logic

### App shell and guards

- `src/middleware.ts`
  - protects app routes (`/dashboard`, `/performance`, `/settings`, etc.)
  - redirects unauthenticated users to `/login`
- `src/app/(app)/layout.tsx`
  - app chrome (bottom nav, chat FAB, tour provider, consent banner)
  - onboarding gate using `/account/onboarding-status`
  - cached onboarding check with reset on sign-out

### API access pattern

- `src/lib/api.ts`
  - `apiFetch(path, options)` reads current Supabase session
  - adds `Authorization: Bearer <token>`
  - throws on non-2xx responses
  - expects JSON responses
- onboarding baseline detection (`/onboarding/detect-baseline`) can now return `baseline_source` values:
  - `race_history` (detected race baseline)
  - `knn_cold_start` (similar-runner estimate when no race history)
  - `cold_start` (25:00 fallback)
- readiness responses (`/readiness`) now include additive `components.injury_risk` plus a corresponding explanatory factor entry.
- projection responses now may include optional metadata:
  - `model_source`
  - `model_confidence`
  - `fallback_reason`
  and frontend dashboard/performance surfaces should render these fields only when present.

## Core Product Surfaces

- `src/app/(app)/dashboard/page.tsx`
  - main projection hub (projection, drivers, readiness, weekly metrics, sync status)
- `src/app/(app)/performance/page.tsx`
  - deep analytics modules (zones, economy, learning, adjuncts, honest state, accuracy)
- `src/app/(app)/chat/page.tsx`
  - thread-based chat with streaming and history restore
- `src/app/(app)/settings/page.tsx`
  - baseline/preferences/wearable and account controls
- `src/app/(app)/event/[eventId]/page.tsx`
  - event-level projection detail, history, trajectory, explanation
- `src/app/(app)/driver/[driverName]/page.tsx`
  - driver-specific trend and contribution detail

## Data Flow in Frontend

1. Middleware resolves auth state from Supabase cookies.
2. App layout enforces onboarding completion before rendering main pages.
3. Pages fetch backend resources via `apiFetch`.
4. Dashboard/performance/event pages map API payloads to UI cards/charts.
5. Realtime channel updates projection/driver state store on new inserts.
6. Chat page persists and restores per-user thread IDs from local storage.

## State Management

- `src/stores/projection-store.ts`
  - current event, projection numbers, drivers, readiness
  - includes `reset()` for clean sign-out transitions
- `src/stores/tour-store.ts`
  - per-user completion keying in local storage
- `src/hooks/use-auth.ts`
  - auth/session listener
  - resets projection/onboarding state on sign-out

## Realtime Contract

- `src/hooks/use-projection-realtime.ts`
  - subscribes to `projection_state` and `driver_state`
  - currently listens to `INSERT` events only
  - filters updates by `user_id` and current event context

## Operational Notes

- Local storage is user-scoped for:
  - chat thread IDs
  - notification preferences
  - tour completion flags
- Async page loaders include cancellation guards to avoid stale updates after unmount.
- If backend is unavailable, some surfaces intentionally degrade gracefully.

## Session Checklist (Frontend)

Before making frontend changes:

1. Read root `README.md` and this file.
2. Confirm impacted route(s), API endpoint(s), and store/hook touchpoints.
3. Add/update tests where behavior changes.
4. Verify auth guard and onboarding flow behavior are preserved.
5. Verify user-scoped persistence is not regressed.
6. Update this README when architecture, route behavior, state flow, or API contracts change.

## README Delta - Onboarding and Readiness Metadata

- **What changed**: Documented onboarding baseline source option `knn_cold_start`, readiness additive injury-risk response metadata, and optional projection model metadata for dashboard/performance display.
- **Why it changed**: Frontend onboarding/readiness/performance modules should distinguish race-history baselines from similar-runner estimates and surface model/risk context without breaking existing rendering.
- **Code touchpoints**: `pirx-backend/app/routers/onboarding.py`, `pirx-backend/app/ml/reference_population.py`, `pirx-backend/app/services/projection_service.py`, `pirx-backend/app/routers/readiness.py`, `pirx-backend/app/ml/injury_risk_model.py`, `pirx-backend/app/routers/projection.py`, `pirx-frontend/src/components/home/projection-tile.tsx`, `pirx-frontend/src/app/(app)/dashboard/page.tsx`, `pirx-frontend/src/app/(app)/performance/page.tsx`.
- **Data-flow impact**: Onboarding baseline detection, initial projection seeding, projection metadata rendering on dashboard/performance, and readiness API consumption in frontend views.
- **Formula/constant changes**: none.
- **API/schema impact**: `/onboarding/detect-baseline` now may return `baseline_source = "knn_cold_start"`; `/readiness` includes `components.injury_risk` and an injury-risk factor; `/projection` may include `model_source`, `model_confidence`, and `fallback_reason`.
- **Verification**: Backend tests `tests/test_onboarding.py`, `tests/test_services_wiring.py::TestProjectionService`, `tests/test_readiness.py`, and `tests/test_projection_endpoints.py` pass for new paths/contracts.

## README Delta - Projection Fallback Provenance

- **What changed**: Clarified that projection metadata (`model_source`, `model_confidence`, `fallback_reason`) now comes from persisted projection rows and can explicitly represent deterministic fallback from non-default selector candidates.
- **Why it changed**: Keep dashboard/performance provenance UI behavior aligned with backend rollout semantics while ML model serving is phased in.
- **Code touchpoints**: `pirx-backend/app/services/projection_service.py`, `pirx-backend/app/services/driver_service.py`, `pirx-backend/app/services/model_orchestrator.py`, `pirx-backend/migrations/014_projection_model_metadata.sql`, `pirx-frontend/src/components/home/projection-tile.tsx`, `pirx-frontend/src/app/(app)/dashboard/page.tsx`, `pirx-frontend/src/app/(app)/performance/page.tsx`.
- **Data-flow impact**: Projection write path now stores fallback provenance that is surfaced by existing frontend cards without requiring breaking UI changes.
- **Formula/constant changes**: none.
- **API/schema impact**: additive `projection_state.fallback_reason`; `projection_state.model_type` now permits `deterministic` alongside ML families.
- **Verification**: Backend compatibility test suite for projection/readiness/onboarding/services wiring passes after metadata persistence updates.

## README Delta - LSTM Projection Source Activation

- **What changed**: Clarified that dashboard/performance projection metadata can now report `model_source = "lstm"` when an active model artifact is available, with deterministic fallback reason only when inference is unavailable.
- **Why it changed**: Frontend provenance display needs to match phased serving behavior as LSTM paths become selectively active.
- **Code touchpoints**: `pirx-backend/app/ml/lstm_inference.py`, `pirx-backend/app/services/projection_service.py`, `pirx-frontend/src/components/home/projection-tile.tsx`, `pirx-frontend/src/app/(app)/dashboard/page.tsx`, `pirx-frontend/src/app/(app)/performance/page.tsx`.
- **Data-flow impact**: Existing projection metadata rendering now distinguishes active LSTM-serving rows from deterministic fallback rows.
- **Formula/constant changes**: none.
- **API/schema impact**: no new frontend contract fields; existing optional projection metadata semantics expanded.
- **Verification**: Backend projection/readiness/onboarding regression suite passes with metadata behavior changes.

## README Delta - Confidence Provenance from Promotion

- **What changed**: Documented that `model_confidence` can now be populated from Optuna promotion confidence metadata on active LSTM registry entries.
- **Why it changed**: Keep frontend confidence display semantics aligned with backend promotion guardrails and tuned-model activation rules.
- **Code touchpoints**: `pirx-backend/app/tasks/ml_tasks.py`, `pirx-backend/app/services/model_orchestrator.py`, `pirx-frontend/src/app/(app)/performance/page.tsx`, `pirx-frontend/src/components/home/projection-tile.tsx`.
- **Data-flow impact**: Projection confidence shown in dashboard/performance can reflect tuned-model quality instead of null/default values when promoted LSTM models are active.
- **Formula/constant changes**: confidence derivation `clamp(1 - best_value, 0, 1)` (backend-driven).
- **API/schema impact**: no API shape changes; existing `model_confidence` optional field semantics extended.
- **Verification**: Backend regression suite passes with updated confidence propagation logic.

## README Delta - Readiness Injury Band Detail

- **What changed**: Documented that readiness injury factor detail now includes explicit risk band text (`low`/`moderate`/`high`) derived from calibrated backend risk probability.
- **Why it changed**: Improve frontend interpretation consistency for readiness risk messaging and reduce ambiguity in user-facing risk context.
- **Code touchpoints**: `pirx-backend/app/ml/injury_risk_model.py`, `pirx-backend/app/routers/readiness.py`, `pirx-frontend/src/app/(app)/performance/page.tsx`.
- **Data-flow impact**: Frontend readiness consumers continue using same response shape but now receive richer injury factor detail text from backend.
- **Formula/constant changes**: none (frontend consumes backend-derived risk bands).
- **API/schema impact**: no contract shape changes; additive semantic detail in readiness factor text.
- **Verification**: Backend readiness and regression test suites pass after risk band persistence updates.

## README Delta - Projection Metadata UX Clarity

- **What changed**: Dashboard `ProjectionTile` and performance `Model & Risk` panel now render human-readable model source labels, confidence bands, and fallback explanations.
- **Why it changed**: Provide explicit rollout-state clarity in UI while retaining backward-compatible metadata contracts.
- **Code touchpoints**: `pirx-frontend/src/components/home/projection-tile.tsx`, `pirx-frontend/src/app/(app)/dashboard/page.tsx`, `pirx-frontend/src/app/(app)/performance/page.tsx`, `pirx-frontend/src/components/home/__tests__/projection-tile.test.tsx`.
- **Data-flow impact**: Existing projection metadata fields are interpreted into user-facing labels (`LSTM model`, confidence tier, deterministic fallback reason) without additional API requests.
- **Formula/constant changes**: frontend confidence tiers (`high >= 80%`, `moderate >= 60%`, else `low`).
- **API/schema impact**: none.
- **Verification**: `npm run test -- "src/components/home/__tests__/projection-tile.test.tsx" "src/app/(auth)/__tests__/login.test.tsx"` passes.

## README Delta - Economy Tab Live Refresh

- **What changed**: Performance `economy` section now refetches `/features/economy` every time the section is opened instead of one-time lazy caching for the whole page session.
- **Why it changed**: Ensure matched-HR band and efficiency values reflect newly synced workouts without requiring a full page reload.
- **Code touchpoints**: `pirx-frontend/src/app/(app)/performance/page.tsx`, `pirx-backend/app/routers/features.py`.
- **Data-flow impact**: Frontend performance analysis fetch behavior plus backend economy-window responsiveness.
- **Formula/constant changes**: none in frontend; backend economy source now emphasizes recent-vs-prior 21-day matched-HR windows.
- **API/schema impact**: none.
- **Verification**: Backend `tests/test_features_endpoints.py` passes after endpoint updates; frontend change is fetch-timing only with unchanged response contract.

## README Delta - Injury Risk Analysis Card

- **What changed**: Added a dedicated `Injury Risk` card in Performance analysis carousel, separate from the broader Event Readiness card.
- **Why it changed**: Improve risk visibility by giving injury risk its own focused analysis surface alongside other performance modules.
- **Code touchpoints**: `pirx-frontend/src/app/(app)/performance/page.tsx`, `pirx-backend/app/routers/readiness.py`.
- **Data-flow impact**: Frontend now loads `/readiness` for both `Event Readiness` and `Injury Risk` analysis cards, deriving risk score and detail from readiness components/factors.
- **Formula/constant changes**: frontend risk-band labels use thresholds aligned to backend semantics (`low < 35`, `moderate < 60`, else `high`).
- **API/schema impact**: none (existing `/readiness` payload reused).
- **Verification**: Manual UI validation path: open Performance -> Analysis -> Injury Risk card after sync/recompute and confirm score/band/detail render.

## README Delta - Dashboard All-Events Projection Parsing

- **What changed**: Dashboard all-events cards now accept projection time from `projected_time_display`, `projected_time_seconds`, or `midpoint_seconds` instead of assuming only one numeric field.
- **Why it changed**: Prevent non-5K event cards from rendering `0s` when backend payloads vary across deploy states or adapters.
- **Code touchpoints**: `pirx-frontend/src/app/(app)/dashboard/page.tsx`, `pirx-backend/app/routers/projection.py`.
- **Data-flow impact**: Frontend dashboard event-swiper rendering only.
- **Formula/constant changes**: none.
- **API/schema impact**: no contract changes; parser is backward/forward compatible with existing payload variants.
- **Verification**: Manual dashboard check after sync/recompute confirms non-5K cards render event-specific projected times.

## README Delta - Dashboard 21-Day Delta Display Guardrail

- **What changed**: Dashboard event cards and projection tile now show `—` for missing or near-zero 21-day deltas instead of always rendering `0s`.
- **Why it changed**: Avoid implying a measured zero shift when the backend has no reliable 21-day delta for that event snapshot.
- **Code touchpoints**: `pirx-frontend/src/app/(app)/dashboard/page.tsx`, `pirx-frontend/src/components/home/projection-tile.tsx`, `pirx-backend/app/routers/projection.py`.
- **Data-flow impact**: Frontend projection display formatting.
- **Formula/constant changes**: display epsilon guardrail for delta labels (`abs(delta) < 0.05` -> `—`).
- **API/schema impact**: no new API fields; uses nullable delta from existing projection endpoints.
- **Verification**: `src/components/home/__tests__/projection-tile.test.tsx` passes and dashboard no longer shows spurious `0s` deltas for unset events.

## README Delta - Baseline Display Consistency

- **What changed**: Baseline race display now consumes backend-normalized auto baseline events so historical 5K defaults are not mislabeled as short-distance events.
- **Why it changed**: Remove confusing baseline labels such as `1500m - 21:00` that came from legacy baseline-event/source mismatches.
- **Code touchpoints**: `pirx-backend/app/routers/account.py`, `pirx-backend/app/services/projection_service.py`, `pirx-frontend/src/app/(app)/performance/page.tsx`.
- **Data-flow impact**: Baseline metadata read/display path in Performance overview.
- **Formula/constant changes**: none.
- **API/schema impact**: none.
- **Verification**: Production baseline read now returns `5000` for auto-source baseline rows and Performance baseline card reflects the corrected label.

## README Delta - Injury Risk Explainability Section

- **What changed**: Added a `Why this number?` expandable explainability block inside the Performance Injury Risk card.
- **Why it changed**: Align injury-risk UX with other explainability surfaces and provide factor-level context for risk score interpretation.
- **Code touchpoints**: `pirx-frontend/src/app/(app)/performance/page.tsx`, `pirx-backend/app/routers/readiness.py`.
- **Data-flow impact**: Frontend now renders readiness factor details (`title`, `detail`, `impact`) directly in Injury Risk analysis.
- **Formula/constant changes**: none.
- **API/schema impact**: none; uses existing `/readiness` `factors` payload.
- **Verification**: Manual UI validation in Performance -> Analysis -> Injury Risk confirms expandable factor breakdown is shown when factors are present.

## README Delta - Economy HR Cost Values

- **What changed**: Performance economy card now receives computed `hr_cost_change` values from backend instead of a static `0%`.
- **Why it changed**: Users were seeing `0%` despite visible matched-HR pace differences.
- **Code touchpoints**: `pirx-backend/app/routers/features.py`, `pirx-frontend/src/app/(app)/performance/page.tsx`.
- **Data-flow impact**: Economy tab read path (`GET /features/economy`).
- **Formula/constant changes**: backend returns percentage-based cost/economy deltas derived from baseline/current matched-HR pace windows.
- **API/schema impact**: none (field names unchanged).
- **Verification**: Backend `tests/test_features_endpoints.py` passes; UI now displays non-zero HR cost change when matched-HR pace shifts.

## README Delta - Economy Why-This-Number Panel

- **What changed**: Added a `Why this number?` collapsible panel to the Performance Economy tab.
- **Why it changed**: Show calculation context for economy metrics so users can interpret `efficiency_gain` and `hr_cost_change` with confidence.
- **Code touchpoints**: `pirx-frontend/src/app/(app)/performance/page.tsx`, `pirx-backend/app/routers/features.py`.
- **Data-flow impact**: Economy tab now reads additive `explanation` metadata from `/features/economy`.
- **Formula/constant changes**: none.
- **API/schema impact**: none (additive response metadata only).
- **Verification**: Backend economy endpoint tests pass; frontend lints clean for updated Economy tab rendering.

## README Delta - Sleep and Body UI Surfaces

- **What changed**: Added dashboard `Recovery & Body` quick view, performance overview `Recovery & Body Signals` card with explainability, and physiology trends support for wearable `custom_fields` body metrics (`weight_kg`, `body_fat_percentage`) plus timestamp-based trend mapping.
- **Why it changed**: Surface Terra sleep/body telemetry in all primary user-facing analytics screens while keeping existing API contracts and graceful empty-state behavior.
- **Code touchpoints**: `pirx-frontend/src/app/(app)/dashboard/page.tsx`, `pirx-frontend/src/app/(app)/performance/page.tsx`, `pirx-frontend/src/app/(app)/physiology/page.tsx`, `pirx-frontend/src/app/(app)/physiology/__tests__/trends-mappers.test.ts`.
- **Data-flow impact**: Frontend now consumes `/physiology/latest` and `/physiology/trends` body/sleep fields and maps them into overview cards and trend charts.
- **Formula/constant changes**: none.
- **API/schema impact**: none; additive rendering of existing `sleep_score` and `custom_fields` values.
- **Verification**: `npm run test:run -- "src/app/(app)/physiology/__tests__/trends-mappers.test.ts" "src/components/home/__tests__/projection-tile.test.tsx"` passes.
