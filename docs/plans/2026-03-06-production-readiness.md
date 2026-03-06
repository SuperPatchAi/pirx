# PIRX Production Readiness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix every gap between the current codebase and the PRD so the app works end-to-end against a real Supabase database with real user sessions.

**Architecture:** Align database schema with application code, wire all mocked endpoints and UI to real data, implement functional onboarding + settings, and add infrastructure (PWA icons, Dockerfiles, observability middleware).

**Tech Stack:** FastAPI, Next.js 16, Supabase PostgreSQL, Celery, LangGraph, Recharts, shadcn/ui, Framer Motion

---

## Phase A — Schema Alignment (CRITICAL)

The migration SQL and application code have diverged on 6+ tables. Every real database query will fail until these are reconciled. We align by writing a new migration (005) that ALTERs the existing tables to match what the code expects.

### Task A1: Write migration 005 to align `projection_state`

**Files:**
- Create: `pirx-backend/migrations/005_schema_alignment.sql`

**Changes:**
- Add columns `range_low_seconds`, `range_high_seconds`, `baseline_seconds`, `volatility` to `projection_state`
- Keep the original `range_lower`, `range_upper`, `confidence_score`, `volatility_score` columns as-is (backwards compat)
- Add `event` CHECK to also allow `'21097'` and `'42195'` (half/full marathon)

```sql
-- 005_schema_alignment.sql

-- A1: projection_state alignment
ALTER TABLE projection_state ADD COLUMN IF NOT EXISTS range_low_seconds FLOAT;
ALTER TABLE projection_state ADD COLUMN IF NOT EXISTS range_high_seconds FLOAT;
ALTER TABLE projection_state ADD COLUMN IF NOT EXISTS baseline_seconds FLOAT;
ALTER TABLE projection_state ADD COLUMN IF NOT EXISTS volatility FLOAT;
ALTER TABLE projection_state DROP CONSTRAINT IF EXISTS projection_state_event_check;
ALTER TABLE projection_state ADD CONSTRAINT projection_state_event_check
  CHECK (event IN ('1500', '3000', '5000', '10000', '21097', '42195'));
```

### Task A2: Align `driver_state` table

**Append to:** `pirx-backend/migrations/005_schema_alignment.sql`

**Changes:**
- Make `projection_id` nullable (code inserts without it)
- Add `event`, `*_score`, `*_trend` columns

```sql
-- A2: driver_state alignment
ALTER TABLE driver_state ALTER COLUMN projection_id DROP NOT NULL;
ALTER TABLE driver_state ADD COLUMN IF NOT EXISTS event TEXT;
ALTER TABLE driver_state ADD COLUMN IF NOT EXISTS aerobic_base_score FLOAT DEFAULT 0;
ALTER TABLE driver_state ADD COLUMN IF NOT EXISTS aerobic_base_trend TEXT DEFAULT 'stable';
ALTER TABLE driver_state ADD COLUMN IF NOT EXISTS threshold_density_score FLOAT DEFAULT 0;
ALTER TABLE driver_state ADD COLUMN IF NOT EXISTS threshold_density_trend TEXT DEFAULT 'stable';
ALTER TABLE driver_state ADD COLUMN IF NOT EXISTS speed_exposure_score FLOAT DEFAULT 0;
ALTER TABLE driver_state ADD COLUMN IF NOT EXISTS speed_exposure_trend TEXT DEFAULT 'stable';
ALTER TABLE driver_state ADD COLUMN IF NOT EXISTS load_consistency_score FLOAT DEFAULT 0;
ALTER TABLE driver_state ADD COLUMN IF NOT EXISTS load_consistency_trend TEXT DEFAULT 'stable';
ALTER TABLE driver_state ADD COLUMN IF NOT EXISTS running_economy_score FLOAT DEFAULT 0;
ALTER TABLE driver_state ADD COLUMN IF NOT EXISTS running_economy_trend TEXT DEFAULT 'stable';
```

### Task A3: Align `activities` table

**Append to:** `pirx-backend/migrations/005_schema_alignment.sql`

**Changes:**
- Add `started_at` as alias column (code uses `started_at`, migration has `timestamp`)
- Widen `activity_type` CHECK to include `'long_run'`, `'tempo'`

```sql
-- A3: activities alignment
ALTER TABLE activities ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
-- Backfill from timestamp
UPDATE activities SET started_at = timestamp WHERE started_at IS NULL;
-- Create index on new column
CREATE INDEX IF NOT EXISTS idx_activities_user_started ON activities(user_id, started_at DESC);
ALTER TABLE activities DROP CONSTRAINT IF EXISTS activities_activity_type_check;
ALTER TABLE activities ADD CONSTRAINT activities_activity_type_check
  CHECK (activity_type IN ('easy', 'threshold', 'interval', 'race', 'cross-training', 'unknown', 'long_run', 'tempo'));
```

### Task A4: Align `users` table

**Append to:** `pirx-backend/migrations/005_schema_alignment.sql`

**Changes:**
- Add `baseline_event`, `baseline_time_seconds`, `baseline_race_date`, `baseline_source` columns
- Widen `primary_event` CHECK for half/full marathon

```sql
-- A4: users alignment
ALTER TABLE users ADD COLUMN IF NOT EXISTS baseline_event TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS baseline_time_seconds FLOAT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS baseline_race_date DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS baseline_source TEXT DEFAULT 'auto';
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_primary_event_check;
ALTER TABLE users ADD CONSTRAINT users_primary_event_check
  CHECK (primary_event IN ('1500', '3000', '5000', '10000', '21097', '42195'));
```

### Task A5: Align `wearable_connections` table

**Append to:** `pirx-backend/migrations/005_schema_alignment.sql`

**Changes:**
- Add `access_token`, `refresh_token`, `athlete_id`, `is_active` columns (code uses plaintext until encryption is added)

```sql
-- A5: wearable_connections alignment
ALTER TABLE wearable_connections ADD COLUMN IF NOT EXISTS access_token TEXT;
ALTER TABLE wearable_connections ADD COLUMN IF NOT EXISTS refresh_token TEXT;
ALTER TABLE wearable_connections ADD COLUMN IF NOT EXISTS athlete_id TEXT;
ALTER TABLE wearable_connections ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
```

### Task A6: Fix `get_recent_activities` to use correct column

**Files:**
- Modify: `pirx-backend/app/services/supabase_client.py`

**Change:** The `get_recent_activities` method queries `started_at` but the table's canonical column is `timestamp`. After migration A3, both exist. Update the method to use `timestamp` as primary (more reliable) and add a `get_activities_since` helper.

```python
def get_recent_activities(self, user_id: str, days: int = 90) -> list[dict]:
    from datetime import datetime, timezone, timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = (
        self.client.table("activities")
        .select("*")
        .eq("user_id", user_id)
        .gte("timestamp", since)
        .order("timestamp", desc=True)
        .execute()
    )
    return result.data or []
```

### Task A7: Deploy migration 005

**Command:** `supabase db push` (or run migration via Supabase dashboard SQL editor)

### Task A8: Run full backend test suite to confirm nothing broke

**Command:** `cd pirx-backend && source venv/bin/activate && pytest -x -q`

---

## Phase B — Onboarding Flow (CRITICAL)

The 5-step onboarding is entirely mocked. A new user cannot connect a wearable, pull history, detect a baseline, or generate a first projection. This phase wires each step to real APIs.

### Task B1: Wire onboarding Step 2 (Connect Wearable) to Strava OAuth

**Files:**
- Modify: `pirx-frontend/src/app/(app)/onboarding/[step]/page.tsx` (ConnectStep component)

**Changes:**
- Replace fake toggle with a "Connect with Strava" button that opens `GET /sync/connect/strava` OAuth URL in a popup/redirect
- On successful OAuth callback (detected via polling `/sync/status`), update the wearable state
- Add a "Skip for now" option

### Task B2: Wire onboarding Step 3 (Loading/Backfill) to real task polling

**Files:**
- Modify: `pirx-frontend/src/app/(app)/onboarding/[step]/page.tsx` (LoadingStep component)
- Modify: `pirx-backend/app/tasks/sync_tasks.py` (backfill_history)

**Backend changes:**
- Implement `backfill_history` for Strava: fetch last 6 months of activities via `StravaService`, normalize, clean, store in DB
- Register the task in `task_registry` so frontend can poll status

**Frontend changes:**
- Replace fake progress timer with polling `GET /sync/status` and checking `task_registry` for the backfill task
- Show real activity count as it accumulates

### Task B3: Wire onboarding Step 4 (Baseline Detection)

**Files:**
- Create: `pirx-backend/app/routers/onboarding.py`
- Modify: `pirx-backend/app/main.py` (register router)
- Modify: `pirx-frontend/src/app/(app)/onboarding/[step]/page.tsx` (BaselineStep)

**Backend changes:**
- New endpoint `POST /onboarding/detect-baseline` that:
  1. Queries user's race activities via `db.get_race_activities(user_id)`
  2. If races found: picks the best recent race, returns it as detected baseline
  3. If no races: uses LMC `cold_start_estimate` from best sustained effort
  4. Returns `{ baseline_event, baseline_time_seconds, baseline_source, detected_races: [] }`
- New endpoint `POST /onboarding/set-baseline` that writes to `users` table

**Frontend changes:**
- On mount, call `POST /onboarding/detect-baseline`
- Display detected race(s) or cold-start estimate
- Let user override by selecting a different race or entering manual time
- On confirm, call `POST /onboarding/set-baseline`

### Task B4: Wire onboarding Step 5 (First Projection + Event Selection)

**Files:**
- Create: `pirx-backend/app/routers/onboarding.py` (add endpoint)
- Modify: `pirx-frontend/src/app/(app)/onboarding/[step]/page.tsx` (RevealStep)

**Backend changes:**
- New endpoint `POST /onboarding/generate-projection` that:
  1. Runs feature engineering on available activities
  2. Computes projection for selected primary event + all other events
  3. Initializes all 5 driver states
  4. Stores `projection_state` and `driver_state` rows
  5. Marks `users.onboarding_completed = true`
  6. Returns the projection data

**Frontend changes:**
- Replace `MOCK_PROJECTIONS` with real API call
- Show real projected times with animation
- On completion, navigate to `/dashboard`

### Task B5: Add onboarding tests

**Files:**
- Create: `pirx-backend/tests/test_onboarding.py`

**Tests:**
- `test_detect_baseline_with_races` — returns best race
- `test_detect_baseline_no_races` — returns cold-start estimate
- `test_set_baseline_writes_to_db`
- `test_generate_projection_creates_states`

---

## Phase C — Settings Page (HIGH)

Most of the Settings page is hardcoded. Wire it to real APIs.

### Task C1: Wire wearable connections list

**Files:**
- Modify: `pirx-frontend/src/app/(app)/settings/page.tsx`

**Changes:**
- Replace `WEARABLE_CONNECTIONS` hardcoded array with `useEffect` fetching `GET /sync/status`
- Display real provider names, `is_active` status, and `last_sync_at`
- "Connect" button opens Strava OAuth or Terra widget
- "Disconnect" button calls `POST /sync/disconnect/{provider}`

### Task C2: Wire disconnect endpoint

**Files:**
- Modify: `pirx-backend/app/routers/sync.py`

**Changes:**
- Implement `disconnect/{provider}`: set `is_active = false` in `wearable_connections`, revoke token if Strava

### Task C3: Wire baseline selection

**Files:**
- Modify: `pirx-frontend/src/app/(app)/settings/page.tsx`

**Changes:**
- Fetch current baseline from `GET /account/baseline`
- Display current baseline event + time
- "Change Baseline" opens a modal that:
  - Fetches race history
  - Lets user select a race or enter manual time
  - Shows warning: "This will recalculate Improvement Since Baseline"
  - On confirm, calls `PUT /account/baseline`

### Task C4: Wire primary event selection

**Files:**
- Modify: `pirx-frontend/src/app/(app)/settings/page.tsx`

**Changes:**
- Fetch current `primary_event` from user profile
- Radio buttons update via `PUT /account/baseline` (add `primary_event` field)
- Persist immediately

### Task C5: Wire notification toggle persistence

**Files:**
- Create: `pirx-backend/app/routers/preferences.py`
- Modify: `pirx-backend/app/main.py`
- Modify: `pirx-frontend/src/app/(app)/settings/page.tsx`

**Backend changes:**
- Add a `user_preferences` table (migration 006) or use `users.custom_fields` JSONB
- Endpoints: `GET /preferences`, `PUT /preferences`
- Store notification toggle states per user

**Frontend changes:**
- Fetch toggles on mount, persist on change

### Task C6: Settings tests

**Files:**
- Modify: `pirx-backend/tests/test_account.py` (add baseline + disconnect tests)
- Create: `pirx-backend/tests/test_preferences.py`

---

## Phase D — Replace Mock Endpoints with Real Data (MEDIUM)

Six backend endpoints return hardcoded data. Wire them to compute from real user features.

### Task D1: Wire `/readiness` to use real user features

**Files:**
- Modify: `pirx-backend/app/routers/readiness.py`

**Changes:**
- Load user's recent activities via `SupabaseService.get_activities()`
- Compute real features via `FeatureService.compute_all_features()`
- Pass real features to `ReadinessEngine.compute()`
- Keep mock fallback for users with no data

### Task D2: Wire `/features/zones` to real data

**Files:**
- Modify: `pirx-backend/app/routers/features.py`

**Changes:**
- Load activities, extract HR zone distributions from `hr_zones` array
- Compute real Z1-Z5 percentages, Z2 efficiency delta
- Classify methodology (Pyramidal/Polarized/Mixed) based on zone distribution ratios

### Task D3: Wire `/features/economy` to real data

**Files:**
- Modify: `pirx-backend/app/routers/features.py`

**Changes:**
- Compute `matched_hr_band_pace` from activities with similar average HR
- Compute efficiency gain at 3 intensity levels
- Use feature service values where available

### Task D4: Wire `/features/learning` and `/features/honest-state` to real data

**Files:**
- Modify: `pirx-backend/app/routers/features.py`

**Changes:**
- Load real feature history (multiple time-point snapshots from `projection_state` and `driver_state`)
- Pass to `LearningModule.analyze_training_patterns()`
- Keep mock fallback for insufficient data

### Task D5: Wire `/features/adjuncts` to real data

**Files:**
- Modify: `pirx-backend/app/routers/features.py`

**Changes:**
- Query `adjunct_state` table for user's adjuncts
- Return real `sessions_analyzed`, `median_projection_delta`, `statistical_status`

### Task D6: Wire `/drivers/{name}/explain` to use real features

**Files:**
- Modify: `pirx-backend/app/routers/drivers.py`

**Changes:**
- Load real features instead of `mock_features`
- Load previous features from prior driver_state for delta computation

### Task D7: Wire chat tool `get_readiness` to real data

**Files:**
- Modify: `pirx-backend/app/chat/tools.py`

**Changes:**
- Same pattern as D1: load activities, compute features, run readiness engine

### Task D8: Wire chat tool `search_insights` (RAG)

**Files:**
- Modify: `pirx-backend/app/chat/tools.py`

**Changes:**
- Replace placeholder with `EmbeddingService.search(user_id, query, match_count=5)`
- Format results as context for the agent

### Task D9: Tests for wired endpoints

**Files:**
- Modify: `pirx-backend/tests/test_features_endpoints.py`
- Modify: `pirx-backend/tests/test_readiness.py`

---

## Phase E — Dashboard & Frontend Wiring (MEDIUM)

### Task E1: Wire EventSwiper to real multi-event data

**Files:**
- Modify: `pirx-frontend/src/app/(app)/dashboard/page.tsx`
- Modify: `pirx-frontend/src/components/home/event-swiper.tsx`

**Changes:**
- Fetch `GET /projection/all` on dashboard mount
- Pass real event data to EventSwiper instead of `apiData={null}`

### Task E2: Wire QuickMetrics to real data

**Files:**
- Modify: `pirx-frontend/src/app/(app)/dashboard/page.tsx`
- Modify: `pirx-frontend/src/components/home/quick-metrics.tsx`

**Changes:**
- Compute sessions/week and distance/week from activities or projection data
- Fetch ACWR from features
- Pass real values as props

### Task E3: Wire SyncBanner to real status

**Files:**
- Modify: `pirx-frontend/src/components/home/sync-banner.tsx`
- Modify: `pirx-frontend/src/app/(app)/dashboard/page.tsx`

**Changes:**
- Fetch `GET /sync/status` on mount
- Display real last_sync_at timestamp
- "Sync Now" triggers a manual sync

### Task E4: Wire `useNotifications` hook

**Files:**
- Modify: `pirx-frontend/src/app/(app)/layout.tsx`

**Changes:**
- Import and call `useNotifications()` in the app layout to register service worker and request permissions

---

## Phase F — Chat Persistence & Thread Storage (HIGH)

### Task F1: Move chat threads from in-memory to Supabase

**Files:**
- Create: `pirx-backend/migrations/006_chat_threads.sql`
- Modify: `pirx-backend/app/routers/chat.py`
- Modify: `pirx-backend/app/services/supabase_client.py`

**Migration:**
```sql
CREATE TABLE chat_threads (
    thread_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE chat_messages (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    thread_id UUID REFERENCES chat_threads(thread_id) ON DELETE CASCADE NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE chat_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_chat_thread_user ON chat_threads(user_id, updated_at DESC);
CREATE INDEX idx_chat_messages_thread ON chat_messages(thread_id, created_at ASC);
```

**Code changes:**
- Replace `_threads` dict with Supabase queries
- `_get_or_create_thread` → inserts into `chat_threads`
- Messages stored in `chat_messages` after each exchange
- History endpoint reads from `chat_messages`

### Task F2: Frontend thread persistence

**Files:**
- Modify: `pirx-frontend/src/app/(app)/chat/page.tsx`

**Changes:**
- Save `threadId` to `localStorage` so refreshing the page resumes the conversation
- Add "New Chat" button to start a fresh thread
- Load previous messages from `/chat/history` on mount

### Task F3: Chat persistence tests

**Files:**
- Modify: `pirx-backend/tests/test_chat_api.py`

---

## Phase G — Celery Task Stubs (MEDIUM)

### Task G1: Implement `backfill_history` for Strava

**Files:**
- Modify: `pirx-backend/app/tasks/sync_tasks.py`

**Changes:**
- Fetch activities from Strava API using stored tokens
- Normalize each activity via `StravaService.normalize_activity()`
- Clean via `CleaningService`
- Store in activities table
- Update task_registry progress

### Task G2: Implement `structural_decay_check`

**Files:**
- Modify: `pirx-backend/app/tasks/projection_tasks.py`

**Changes:**
- Query all users with `onboarding_completed = true`
- For each user: check days since last activity
- If > 10 days: widen supported range, trigger notification
- If > 21 days: mark projection as stale

### Task G3: Implement `weekly_summary`

**Files:**
- Modify: `pirx-backend/app/tasks/projection_tasks.py`

**Changes:**
- Query users with notifications enabled
- For each: compute last 7 days stats (projection change, driver shifts, volume)
- Create notification_log entry with summary text and deep_link

### Task G4: Implement `bias_correction`

**Files:**
- Modify: `pirx-backend/app/tasks/projection_tasks.py`

**Changes:**
- For users with actual race results stored: compare projected vs actual
- Compute bias, apply correction factor to future projections
- Log metrics to `model_metrics` table

### Task G5: Task tests

**Files:**
- Modify: `pirx-backend/tests/test_tasks.py`

---

## Phase H — Auth & Security (HIGH)

### Task H1: Add Google Sign-In to login/signup pages

**Files:**
- Modify: `pirx-frontend/src/app/login/page.tsx`
- Modify: `pirx-frontend/src/app/signup/page.tsx`

**Changes:**
- Add "Continue with Google" button using `supabase.auth.signInWithOAuth({ provider: 'google' })`
- Configure Google OAuth in Supabase Dashboard (requires Google Cloud Console setup)

### Task H2: Add Apple Sign-In to login/signup pages

**Files:**
- Modify: `pirx-frontend/src/app/login/page.tsx`
- Modify: `pirx-frontend/src/app/signup/page.tsx`

**Changes:**
- Add "Continue with Apple" button using `supabase.auth.signInWithOAuth({ provider: 'apple' })`
- Configure Apple Sign-In in Supabase Dashboard (requires Apple Developer account)

### Task H3: Ensure user row creation on first login

**Files:**
- Modify: `pirx-frontend/src/app/auth/callback/route.ts` or create Supabase trigger

**Changes:**
- After successful auth, check if user exists in `users` table
- If not, create user row with `user_id` from auth.uid and email
- Redirect to `/onboarding/1` for new users, `/dashboard` for existing

---

## Phase I — Infrastructure & Polish (MEDIUM)

### Task I1: Generate PWA icons

**Files:**
- Create: `pirx-frontend/public/icon-72.png`
- Create: `pirx-frontend/public/icon-192.png`
- Create: `pirx-frontend/public/icon-512.png`

**Changes:**
- Generate PIRX branded icons at required sizes
- Update `manifest.json` if needed

### Task I2: Add FastAPI request logging middleware

**Files:**
- Create: `pirx-backend/app/middleware/logging.py`
- Modify: `pirx-backend/app/main.py`

**Changes:**
- Middleware that logs request method, path, status code, and latency
- Structured JSON logging for production

### Task I3: Create Dockerfiles

**Files:**
- Create: `pirx-backend/Dockerfile`
- Create: `docker-compose.yml`

**Changes:**
- Backend Dockerfile: Python 3.12, install requirements, uvicorn CMD
- docker-compose: backend + redis + celery worker

### Task I4: Create `.env.example` files

**Files:**
- Create: `pirx-backend/.env.example`
- Create: `pirx-frontend/.env.local.example`

**Changes:**
- Document all required env vars with placeholder values
- Include comments explaining each var

### Task I5: Add Sentry integration

**Files:**
- Modify: `pirx-backend/requirements.txt`
- Modify: `pirx-backend/app/main.py`
- Modify: `pirx-frontend/src/app/layout.tsx` or `next.config.ts`

**Changes:**
- Backend: `sentry_sdk.init()` with DSN from env
- Frontend: `@sentry/nextjs` with client + server init
- Requires `SENTRY_DSN` env var

### Task I6: Create GitHub Actions CI pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

**Changes:**
- On push/PR: run backend tests (pytest), frontend build (next build), lint
- Matrix: Python 3.12, Node 20

---

## Phase J — Adjunct Library CRUD (LOW)

### Task J1: Implement adjunct library backend

**Files:**
- Modify: `pirx-backend/app/routers/account.py`

**Changes:**
- `GET /account/adjunct-library` → query `adjunct_state` table
- `POST /account/adjunct-library` → insert new adjunct into `adjunct_state`
- `DELETE /account/adjunct-library/{id}` → delete from `adjunct_state`

### Task J2: Wire adjunct library UI in Settings

**Files:**
- Modify: `pirx-frontend/src/app/(app)/settings/page.tsx`

**Changes:**
- Fetch real adjunct list
- Add/delete adjuncts via API

---

## Execution Order & Dependencies

```
Phase A (Schema) ──→ Phase B (Onboarding) ──→ Phase D (Mock Endpoints)
                 ──→ Phase C (Settings)
                 ──→ Phase F (Chat Persistence)
                 ──→ Phase G (Celery Tasks)

Phase B ──→ Phase E (Dashboard Wiring)
Phase D ──→ Phase E

Phase H (Auth) can run in parallel with A-E
Phase I (Infrastructure) can run in parallel with everything
Phase J (Adjuncts) depends on Phase A
```

**Estimated task count:** 43 tasks across 10 phases
**Critical path:** A → B → D → E (must be sequential)

---

## Commit Strategy

Commit after each completed phase:
1. `fix: align database schema with application code (Phase A)`
2. `feat: wire onboarding flow to real APIs (Phase B)`
3. `feat: wire settings page to real APIs (Phase C)`
4. `feat: replace mock endpoints with real user data (Phase D)`
5. `feat: wire dashboard components to real data (Phase E)`
6. `feat: persist chat threads to Supabase (Phase F)`
7. `feat: implement Celery background tasks (Phase G)`
8. `feat: add Google + Apple social auth (Phase H)`
9. `chore: add Docker, CI, Sentry, PWA icons (Phase I)`
10. `feat: implement adjunct library CRUD (Phase J)`
