# PIRX Architecture Reference — End-to-End Tech Stack

> Version 1.0 | March 2026
> AI-Native Running Performance Intelligence Application

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Frontend — Mobile-First Web App](#2-frontend--mobile-first-web-app)
3. [Backend — API & Orchestration Layer](#3-backend--api--orchestration-layer)
4. [Database & Storage](#4-database--storage)
5. [ML/AI Engine — Projection & Prediction](#5-mlai-engine--projection--prediction)
6. [Conversational AI — Chat With Your Data](#6-conversational-ai--chat-with-your-data)
7. [Wearable Data Integration Layer](#7-wearable-data-integration-layer)
8. [Background Processing & Task Queue](#8-background-processing--task-queue)
9. [Authentication & Authorization](#9-authentication--authorization)
10. [Deployment & Infrastructure](#10-deployment--infrastructure)
11. [Observability & Monitoring](#11-observability--monitoring)
12. [Testing Strategy](#12-testing-strategy)
13. [Data Privacy & Compliance](#13-data-privacy--compliance)
14. [Full Dependency Manifest](#14-full-dependency-manifest)

---

## 1. Architecture Overview

### System Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │  Next.js PWA │  │ iOS Wrapper  │  │  Android Wrapper (TWA)   │ │
│  │  (React/TS)  │  │ (WKWebView + │  │  Trusted Web Activity    │ │
│  │  shadcn/ui   │  │  HealthKit)  │  │  + Health Connect        │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────────┘ │
└─────────┼─────────────────┼─────────────────────┼─────────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌───────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                            │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              Supabase Edge Functions (Deno)                 │  │
│  │         Auth · RLS · Realtime · REST/GraphQL                │  │
│  └──────────────────────────┬──────────────────────────────────┘  │
│                             │                                     │
│  ┌──────────────────────────▼──────────────────────────────────┐  │
│  │              FastAPI (Python 3.12+)                          │  │
│  │     ML Serving · Projection Engine · Chat Agent             │  │
│  │     Wearable Sync · Feature Engineering                     │  │
│  └──────────────────────────┬──────────────────────────────────┘  │
└─────────────────────────────┼─────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────┐  ┌───────────────────┐  ┌──────────────────┐
│  Supabase    │  │   Redis           │  │  Celery Workers  │
│  PostgreSQL  │  │   (Cache + Broker)│  │  (Background ML) │
│  + pgvector  │  │                   │  │                  │
└──────────────┘  └───────────────────┘  └──────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────┐  ┌───────────────────┐  ┌──────────────────┐
│  Wearable    │  │   LLM Provider    │  │  Supabase        │
│  APIs        │  │   (OpenAI /       │  │  Storage         │
│  (Terra +    │  │    Anthropic)     │  │  (FIT files,     │
│   Direct)    │  │                   │  │   exports)       │
└──────────────┘  └───────────────────┘  └──────────────────┘
```

### Design Principles

1. **Projection-first**: Every architectural decision serves the projection engine
2. **AI-native**: LLM conversational interface as a first-class citizen, not an afterthought
3. **Per-runner personalization**: Individual models per user, not one global model
4. **Privacy by design**: Health data stays in Supabase with RLS; no third-party analytics on raw user data
5. **Progressive enhancement**: Web-first PWA, native wrappers only for HealthKit/Health Connect access

---

## 2. Frontend — Mobile-First Web App

### Core Stack

| Technology | Version | Purpose |
|---|---|---|
| **Next.js** | 16.x (App Router) | React framework, SSR/SSG, API routes, PWA |
| **React** | 19.x | UI component library |
| **TypeScript** | 5.x | Type safety across codebase |
| **shadcn/ui** | latest | Component system (Radix + Tailwind) |
| **Tailwind CSS** | 4.x | Utility-first styling |
| **Framer Motion** | 12.x | Animation (projection transitions, charts) |
| **Recharts** | 2.x | Data visualization (projection chart, driver trends) |
| **next-pwa** | latest | Service worker, offline support, push notifications |

### Key Frontend Libraries

| Library | Purpose |
|---|---|
| `@supabase/supabase-js` | Client-side Supabase SDK (auth, realtime, storage) |
| `@supabase/ssr` | Server-side Supabase helpers for Next.js App Router |
| `swr` or `@tanstack/react-query` | Client-side data fetching, cache, optimistic updates |
| `zustand` | Lightweight global state (projection state, user prefs) |
| `zod` | Runtime schema validation (API responses, form data) |
| `date-fns` | Date manipulation (training windows, block calculations) |
| `react-hook-form` | Form management (physiology entry, settings) |
| `lucide-react` | Icon system (consistent with shadcn/ui) |
| `vaul` | Drawer component (mobile-optimized sheets) |
| `cmdk` | Command palette (power-user quick actions) |
| `ai` (Vercel AI SDK) | Streaming chat UI, message handling for AI chat |

### PWA Configuration

```
manifest.json:
  display: standalone
  orientation: portrait
  theme_color: PIRX brand
  start_url: /dashboard
  scope: /

Service Worker:
  Cache strategy: stale-while-revalidate for API data
  Offline: Show last cached projection with "offline" badge
  Push: projection-shift, readiness-shift, weekly-summary
```

### Native Wrappers (Phase 2)

| Platform | Approach | Why |
|---|---|---|
| **iOS** | WKWebView wrapper + native HealthKit bridge | Apple has no REST API for HealthKit — requires on-device Swift code |
| **Android** | Trusted Web Activity (TWA) + Health Connect bridge | Google Fit REST API deprecated 2026; Health Connect is on-device only |

The native wrappers are thin shells. All business logic lives in the Next.js PWA. The wrappers exist solely to bridge platform-specific health APIs (HealthKit, Health Connect) and forward data to the PIRX backend.

---

## 3. Backend — API & Orchestration Layer

### Dual Backend Architecture

PIRX uses two backend layers, each optimized for its workload:

#### Layer 1: Supabase Edge Functions (TypeScript/Deno)

| Function | Purpose |
|---|---|
| Auth callbacks | OAuth flows for Strava, Garmin, Fitbit |
| Webhook receivers | Incoming wearable data notifications |
| Realtime triggers | Database change notifications to frontend |
| Lightweight CRUD | User settings, physiology manual entry |
| Embedding generation | pgvector embeddings for chat RAG |

#### Layer 2: FastAPI (Python 3.12+)

| Module | Purpose |
|---|---|
| `/projection` | Projection engine computation |
| `/drivers` | Driver state calculation and attribution |
| `/readiness` | Event Readiness scoring |
| `/chat` | LangGraph conversational agent |
| `/sync` | Wearable data ingestion and normalization |
| `/features` | Feature engineering pipeline |
| `/models` | ML model serving (inference) |
| `/health` | Health check, metrics |

### FastAPI Dependencies

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.128+ | Async web framework |
| `uvicorn` | 0.34+ | ASGI server |
| `pydantic` | 2.x | Request/response validation |
| `httpx` | 0.28+ | Async HTTP client (wearable API calls) |
| `python-jose[cryptography]` | latest | JWT token validation |
| `supabase-py` | latest | Python Supabase client |

### API Design Principles

- All endpoints return projections in **seconds** (PIRX's unit of truth)
- Driver adjustments always sum to total improvement (enforced server-side)
- Projection state is immutable — new states are appended, never mutated
- WebSocket endpoint at `/ws/projection` for realtime projection streaming during chat

---

## 4. Database & Storage

### Supabase PostgreSQL

| Feature | Usage |
|---|---|
| **Core tables** | Users, Activities, Intervals, Physiology, Projection_State, Driver_State, Adjunct_State (see reference.md schema) |
| **pgvector extension** | Vector embeddings for semantic search in chat RAG |
| **Row Level Security** | All tables protected; users can only access their own data |
| **Realtime** | Subscription on Projection_State and Driver_State changes |
| **Database Functions** | `query_embeddings()`, `compute_rolling_features()`, trigger functions |
| **Cron (pg_cron)** | Scheduled structural decay checks, weekly summary generation |

### Vector Store for Chat RAG

```sql
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

CREATE TABLE user_embeddings (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  user_id UUID REFERENCES users(user_id),
  content_type TEXT NOT NULL,  -- 'activity_summary', 'projection_change', 'insight', 'driver_shift'
  content TEXT NOT NULL,
  metadata JSONB,
  embedding extensions.vector(1536),
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE user_embeddings ENABLE ROW LEVEL SECURITY;
CREATE INDEX ON user_embeddings USING hnsw (embedding vector_cosine_ops);
```

Every projection change, driver shift, notable workout, and insight is embedded and stored for the chat agent to retrieve.

### Redis (Upstash or self-hosted)

| Use Case | Details |
|---|---|
| Celery broker | Task queue message broker |
| Session cache | User session data, recent projection state |
| Rate limiting | Wearable API rate limit tracking |
| Feature cache | Pre-computed rolling features (7d, 21d, 42d windows) |

### Supabase Storage

| Bucket | Contents |
|---|---|
| `fit-files` | Raw FIT/GPX/TCX files from wearable syncs |
| `exports` | User data exports (GDPR compliance) |
| `model-artifacts` | Per-user serialized ML model weights |

---

## 5. ML/AI Engine — Projection & Prediction

### Python ML Stack

| Package | Version | PIRX Use Case |
|---|---|---|
| **PyTorch** | 2.8+ | LSTM per-runner models, CNN+LSTM fatigue classification |
| **scikit-learn** | 1.7+ | KNN (k=3), Random Forest (injury risk), Gradient Boosting (driver regression), SVM (zone classification) |
| **NumPy** | 2.x | Matrix operations, LMC algorithm (`linalg.lstsq`), Riegel formula |
| **pandas** | 2.x | Feature engineering, rolling windows, data cleaning pipeline |
| **scipy** | 1.x | DTW (`scipy.spatial.distance`), statistical tests, Bland-Altman analysis |
| **Optuna** | 4.7+ | Hyperparameter optimization (60 trials per runner model) |
| **SHAP** | 0.46+ | Explainable AI — driver contribution explanations |
| **dtaidistance** | 2.x | Dynamic Time Warping for workout alignment |
| **joblib** | 1.x | Model serialization/deserialization |

### Model Registry

Each PIRX user gets personalized models. The model lifecycle:

```
1. User onboarding → baseline estimation (LMC rank 2 or sustained-effort proxy)
2. First 4 weeks → KNN (k=3) for similar-runner seeding
3. 8+ weeks of data → per-user LSTM trained via Optuna (60 trials)
4. Continuous → Gradient Boosting for driver-to-projection regression
5. Race events → LMC recalibration with new race data
```

### Model Specifications (from research)

#### LMC Rank 2 (Event Scaling)
```
Algorithm: det(A)=0 on sub-pattern matrices
Components: f1, f2, f3 pre-computed per distance
Runner params: λ1, λ2, λ3 estimated via least-squares
Accuracy: 2% rel.MAE (elite), RMSE 0.0515 (log-time)
Cold start: Sustained-effort proxy with reduced confidence
```

#### KNN (Similar Runner Matching)
```
k: 3
Distance: Euclidean
Weighting: Inverse distance (1/d)
Features: [10km_time, BMI, age, sex]
Accuracy: MAE 2.4% (4 min 48s for marathon)
```

#### Per-Runner LSTM (Projection Engine)
```
Neurons: 17
Sequence length: 11
Batch size: 56
Learning rate: 0.018468
Dropout: 50%
Loss: Huber (robust to outliers)
Optimizer: Adam
HPO: Optuna, 60 trials
Framework: PyTorch
```

#### Gradient Boosting (Driver Attribution)
```
Learning rate: 0.0075-0.0092
Epochs: 250-275
Batch size: 64
Dropout: 0.35-0.40
L2 regularization: 0.0018-0.0025
Features: 27 engineered features across 5 domains
```

#### CNN+LSTM (Fatigue Classification)
```
Input: [ACC, GYR, POS] 9-channel IMU (when available)
Fallback: HR + RPE proxy
Window: 200 samples, 50% overlap
LSTM hidden units: 128
Accuracy: 99.62% (3-stage classification)
```

#### Random Forest (Injury Risk)
```
Output: Continuous probability (NOT binary)
Top features: ACL Risk Score (0.394), Load Balance (0.218)
Accuracy: 0.98, ROC-AUC: 0.97
Used for: Readiness score decay, risk warnings
```

### Feature Engineering Pipeline

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

### Projection Formula

```
Projected Time = Baseline Time
                 - Aerobic Adjustment
                 - Threshold Adjustment
                 - Speed Adjustment
                 - Economy Adjustment
                 - Consistency Adjustment

Rolling Window Weights:
  Recent 7 days:  0.45
  Days 8-21:      0.35
  Days 22-90:     0.20

Volatility Dampening:
  Smoothed = α × new_projection + (1 - α) × previous_projection
  Where α ∈ [0.3, 0.7]
```

### Validation Standards

All models validated using:
- **Huber loss** for training (robust to GPS/data outliers)
- **Bland-Altman analysis** for projection accuracy (Bias ± 95% LoA)
- **Acceptance criteria**: MAE < 5%, Cohen's d ≤ 0.1
- **Iterative bias correction loop** with ε = 0.01 convergence threshold

---

## 6. Conversational AI — Chat With Your Data

### Architecture: LangGraph Agent

PIRX's AI chat allows users to ask natural language questions about their running data, projections, and training patterns.

| Component | Technology | Purpose |
|---|---|---|
| **Agent Framework** | LangGraph 1.0+ | Stateful agent graph with checkpointing |
| **LLM** | OpenAI GPT-4.1 / Anthropic Claude | Reasoning, natural language generation |
| **Embeddings** | OpenAI `text-embedding-3-small` (1536d) | Vector embeddings for RAG |
| **Vector Store** | Supabase pgvector | Per-user semantic search |
| **Memory** | LangGraph PostgresSaver | Conversation persistence per thread |
| **Streaming** | Vercel AI SDK + FastAPI WebSocket | Token-by-token response streaming |

### LangGraph Agent Design

```
                     ┌─────────────┐
                     │    START     │
                     └──────┬──────┘
                            ▼
                ┌───────────────────────┐
                │  classify_intent      │
                │  (route user query)   │
                └───────────┬───────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                  ▼
┌─────────────────┐ ┌──────────────┐ ┌────────────────┐
│ projection_query│ │ training_    │ │ general_chat   │
│ (RAG + tools)   │ │ analysis     │ │ (direct LLM)   │
│                 │ │ (SQL + tools)│ │                │
└────────┬────────┘ └──────┬───────┘ └────────┬───────┘
         │                 │                   │
         ▼                 ▼                   ▼
┌────────────────────────────────────────────────────┐
│              generate_response                      │
│  (synthesize answer with PIRX terminology rules)   │
└────────────────────────────────────────────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │     END     │
                     └─────────────┘
```

### Agent Tools

| Tool | Description |
|---|---|
| `get_projection` | Retrieve current projection state (midpoint, range, confidence) |
| `get_drivers` | Retrieve driver breakdown with 21-day trends |
| `get_training_history` | Query activities with date range, type filters |
| `get_readiness` | Event Readiness scores across distances |
| `get_physiology` | HR, HRV, sleep trends |
| `search_insights` | Semantic search over embedded insights/projection changes |
| `compare_periods` | Compare two training blocks (DTW alignment) |
| `explain_driver` | SHAP-based explanation of why a driver changed |

### RAG Pipeline

1. **Embed on write**: Every projection change, notable workout, driver shift gets embedded via `text-embedding-3-small` and stored in `user_embeddings`
2. **Retrieve on query**: User question → embed → cosine similarity search → top-k context
3. **Generate**: LLM receives context + user question + PIRX terminology rules → response
4. **Guard rails**: Response must use PIRX locked terminology (Projected Time, not "predicted time")

### Python Dependencies for Chat

| Package | Purpose |
|---|---|
| `langchain` | LLM abstractions, tool definitions, prompt templates |
| `langgraph` | Stateful agent graph, checkpointing, streaming |
| `langgraph-checkpoint-postgres` | Persistent conversation memory via PostgreSQL |
| `langchain-openai` | OpenAI model and embedding integrations |
| `langchain-anthropic` | Anthropic Claude integration |
| `openai` | Direct OpenAI SDK (embeddings, fallback) |
| `tiktoken` | Token counting for context window management |

---

## 7. Wearable Data Integration Layer

### Strategy: Hybrid (Terra API + Direct Integrations)

| Platform | Integration Method | Data Access | Auth |
|---|---|---|---|
| **Garmin** | Terra API + Garmin Health API (direct) | HR, HRV, sleep, stress, activities, FIT files | OAuth 2.0 via Garmin Connect |
| **Strava** | Direct API | Activities, GPS tracks, segments, efforts | OAuth 2.0 (webhook subscription) |
| **Apple Health** | iOS native bridge → PIRX backend | All HealthKit data types | On-device permission (no REST API) |
| **Google Health Connect** | Android native bridge → PIRX backend | All Health Connect data types | On-device permission (Google Fit REST deprecated 2026) |
| **Fitbit** | Terra API + Fitbit Web API (direct) | HR, sleep, activities, SpO2 | OAuth 2.0 PKCE |
| **Suunto** | Terra API + Suunto Cloud API | FIT files, HR, GPS, altitude | OAuth 2.0 via Suunto API Zone |
| **COROS** | Terra API + COROS Open API | Activities, HR, GPS, FIT files | OAuth 2.0 via COROS partner program |
| **WHOOP** | Terra API | Strain, recovery, sleep, HRV | OAuth 2.0 |
| **Oura** | Terra API | Sleep, readiness, HRV, temperature | OAuth 2.0 |
| **Polar** | Terra API | HR, activities, sleep, Orthostatic test | OAuth 2.0 |

### Why Hybrid (Terra + Direct)?

- **Terra** (tryterra.co) provides a unified schema across 500+ wearables, handles auth flows, and delivers webhooks. This covers the long tail of devices.
- **Direct APIs** for Garmin, Strava, Fitbit give deeper data access (raw FIT files, interval-level data, webhook subscriptions) that Terra may not expose.
- PIRX uses Terra as the default and adds direct integrations for platforms where deeper data is critical for the projection engine.

### Terra API Integration

| Feature | Details |
|---|---|
| Base URL | `https://api.tryterra.co/v2` |
| Auth | API key + webhook secret |
| User connection | Terra widget (drop-in OAuth UI) |
| Data delivery | Webhooks (push) + REST (pull for history) |
| Data types | Activity, Sleep, Body, Daily, Nutrition |
| Normalization | Terra normalizes all device data into unified JSON schema |

### Wearable Data Sync Flow

```
1. User connects wearable (Terra widget or direct OAuth)
2. Historical pull: GET /v2/activity?start_date=6_months_ago
3. Webhook registered: POST notifications on new activity/sleep/body
4. On webhook receive:
   a. Validate webhook signature
   b. Store raw data in activities/physiology tables
   c. Queue feature engineering job (Celery)
   d. If structural shift threshold met → recompute projection
   e. Push realtime update to frontend via Supabase Realtime
```

### Data Normalization Pipeline

```python
NORMALIZED_ACTIVITY = {
    'source': str,            # 'garmin', 'strava', 'apple_health', etc.
    'timestamp': datetime,
    'duration_seconds': int,
    'distance_meters': float,
    'avg_hr': Optional[int],
    'max_hr': Optional[int],
    'avg_pace_sec_per_km': Optional[float],
    'elevation_gain_m': Optional[float],
    'calories': Optional[int],
    'activity_type': str,     # mapped to PIRX types: easy, threshold, interval, race, cross-training
    'hr_zones': Optional[List[float]],  # time-in-zone array
    'laps': Optional[List[dict]],       # interval-level data
    'fit_file_url': Optional[str],      # raw FIT file in storage
}
```

### Python Dependencies for Wearable Integration

| Package | Purpose |
|---|---|
| `httpx` | Async HTTP client for all wearable API calls |
| `fitparse` | Parse raw FIT files from Garmin/Suunto/COROS |
| `gpxpy` | Parse GPX files |
| `tcxparser` | Parse TCX files |
| `cryptography` | Webhook signature verification |

---

## 8. Background Processing & Task Queue

### Celery + Redis

| Component | Technology |
|---|---|
| Task queue | Celery 5.x |
| Broker | Redis |
| Result backend | Redis (short-lived) or PostgreSQL (audit trail) |
| Scheduler | Celery Beat (periodic tasks) |

### Task Categories

| Task | Priority | Trigger | Duration |
|---|---|---|---|
| `feature_engineering` | High | Activity sync webhook | 2-5 sec |
| `recompute_projection` | High | Feature shift threshold met | 5-15 sec |
| `train_user_model` | Low | Weekly or on 20+ new activities | 30-120 sec |
| `generate_embeddings` | Medium | Projection change, insight generated | 1-3 sec |
| `structural_decay_check` | Medium | Daily cron (pg_cron) | 1 sec/user |
| `weekly_summary` | Low | Weekly cron | 5-10 sec/user |
| `wearable_backfill` | Low | New wearable connection | 30-300 sec |
| `bias_correction` | Low | Monthly cron | 10-30 sec/user |

### Celery Configuration

```python
CELERY_CONFIG = {
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/1',
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
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

---

## 9. Authentication & Authorization

### Auth Stack

| Component | Technology |
|---|---|
| Primary auth | Supabase Auth (email/password, magic link) |
| Social auth | Supabase Auth (Google, Apple Sign-In) |
| Wearable OAuth | Custom OAuth 2.0 flows per platform (stored as encrypted tokens) |
| Session management | Supabase JWT (access + refresh tokens) |
| API auth | Supabase JWT verification in FastAPI middleware |
| RLS | Row Level Security on all Supabase tables |

### OAuth Token Storage

Wearable API tokens (Garmin, Strava, Fitbit, etc.) stored in an encrypted `wearable_connections` table:

```sql
CREATE TABLE wearable_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(user_id) NOT NULL,
  provider TEXT NOT NULL,            -- 'garmin', 'strava', 'fitbit', 'terra'
  access_token_encrypted TEXT,
  refresh_token_encrypted TEXT,
  token_expires_at TIMESTAMPTZ,
  terra_user_id TEXT,                -- Terra's internal user reference
  scopes TEXT[],
  connected_at TIMESTAMPTZ DEFAULT now(),
  last_sync_at TIMESTAMPTZ
);

ALTER TABLE wearable_connections ENABLE ROW LEVEL SECURITY;
```

---

## 10. Deployment & Infrastructure

### Production Architecture

| Component | Platform | Why |
|---|---|---|
| **Frontend** | Vercel | Native Next.js hosting, edge CDN, preview deployments |
| **FastAPI backend** | Railway or Render (containerized) | GPU-optional containers, auto-scaling, health checks |
| **Database** | Supabase (managed Postgres) | Managed Postgres with pgvector, realtime, auth, edge functions |
| **Redis** | Upstash (serverless Redis) | Serverless, pay-per-request, global replication |
| **Celery workers** | Railway or Render (background workers) | Dedicated container for ML tasks |
| **ML model storage** | Supabase Storage + optional S3 | Per-user model artifacts |
| **Monitoring** | Sentry + Supabase Observability | Error tracking, performance monitoring |
| **CI/CD** | GitHub Actions | Test, lint, build, deploy pipeline |

### Docker Containers

```
pirx-api/
  Dockerfile          → FastAPI + uvicorn
  requirements.txt    → Python dependencies

pirx-worker/
  Dockerfile          → Celery worker with ML libs
  requirements.txt    → Same Python deps + torch

pirx-frontend/
  Deployed via Vercel (no container needed)
```

### Environment Configuration

```
# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_URL=

# LLM
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Wearable APIs
TERRA_API_KEY=
TERRA_WEBHOOK_SECRET=
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
GARMIN_CONSUMER_KEY=
GARMIN_CONSUMER_SECRET=
FITBIT_CLIENT_ID=
FITBIT_CLIENT_SECRET=

# Infrastructure
REDIS_URL=
CELERY_BROKER_URL=

# App
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=
```

---

## 11. Observability & Monitoring

| Layer | Tool | Metrics |
|---|---|---|
| **Frontend** | Vercel Analytics + Sentry | Core Web Vitals, JS errors, user flows |
| **API** | Sentry + custom FastAPI middleware | Request latency, error rates, endpoint usage |
| **ML Models** | Custom metrics → Supabase table | Projection accuracy (MAE), bias drift, model staleness |
| **Celery** | Flower (Celery monitoring) | Queue depth, task duration, failure rate |
| **Database** | Supabase Dashboard + pg_stat | Query performance, connection pool, storage |
| **Wearable sync** | Custom metrics | Sync success rate per provider, latency, data freshness |

### Model Accuracy Monitoring

```sql
CREATE TABLE model_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(user_id),
  metric_date DATE NOT NULL,
  model_type TEXT NOT NULL,           -- 'lstm', 'knn', 'lmc', 'gradient_boost'
  mae_seconds FLOAT,
  bias_seconds FLOAT,
  bland_altman_lower FLOAT,
  bland_altman_upper FLOAT,
  cohens_d FLOAT,
  sample_size INT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 12. Testing Strategy

### Test-Driven Development (TDD)

Every feature follows Red → Green → Refactor.

| Layer | Framework | Coverage Target |
|---|---|---|
| **Frontend** | Vitest + React Testing Library | 80%+ component tests |
| **Frontend E2E** | Playwright | Critical user flows (onboarding, projection view, chat) |
| **FastAPI** | pytest + httpx (TestClient) | 90%+ endpoint coverage |
| **ML Models** | pytest + custom fixtures | Accuracy thresholds per model type |
| **Database** | pgTAP (PostgreSQL testing) | RLS policies, trigger functions |
| **Integration** | pytest + Docker Compose | End-to-end data flow: sync → features → projection |

### ML-Specific Test Strategy

```python
# Projection accuracy gate — blocks deployment if regression detected
def test_projection_accuracy():
    test_runners = load_test_cohort()  # 50 runners with known outcomes
    predictions = model.predict(test_runners)
    mae = mean_absolute_error(actuals, predictions)
    assert mae < THRESHOLD_SECONDS, f"MAE {mae}s exceeds {THRESHOLD_SECONDS}s"

# Bland-Altman validation
def test_bland_altman():
    bias = np.mean(actuals - predictions)
    sd = np.std(actuals - predictions)
    cohens_d = abs(bias) / sd
    assert cohens_d <= 0.1, f"Cohen's d {cohens_d} exceeds trivial threshold"
```

---

## 13. Data Privacy & Compliance

| Regulation | Scope | Implementation |
|---|---|---|
| **PIPEDA** (Canada) | All Canadian users | Consent on collection, purpose limitation, data portability |
| **GDPR** (EU) | All EU users | Right to erasure, data export, DPA with Supabase |
| **HIPAA-adjacent** (US) | Blood/lactate data | Encryption at rest, audit logs, BAA with Supabase if needed |

### Technical Controls

- All data encrypted at rest (Supabase default: AES-256)
- All data encrypted in transit (TLS 1.3)
- Wearable OAuth tokens encrypted at application layer before storage
- RLS enforces user-level data isolation at the database level
- Data export endpoint: `GET /v1/user/export` → generates complete JSON/CSV
- Data deletion endpoint: `DELETE /v1/user/data` → cascading delete + confirmation
- Audit log table for all data access

---

## 14. Full Dependency Manifest

### Frontend (`package.json`)

```json
{
  "dependencies": {
    "next": "^16.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "typescript": "^5.6.0",
    "@supabase/supabase-js": "^2.48.0",
    "@supabase/ssr": "^0.6.0",
    "tailwindcss": "^4.0.0",
    "@tanstack/react-query": "^5.62.0",
    "zustand": "^5.0.0",
    "zod": "^3.24.0",
    "react-hook-form": "^7.54.0",
    "@hookform/resolvers": "^3.9.0",
    "recharts": "^2.15.0",
    "framer-motion": "^12.0.0",
    "date-fns": "^4.1.0",
    "lucide-react": "^0.470.0",
    "vaul": "^1.1.0",
    "cmdk": "^1.0.0",
    "ai": "^4.1.0",
    "next-pwa": "^5.6.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.6.0"
  },
  "devDependencies": {
    "vitest": "^3.0.0",
    "@testing-library/react": "^16.1.0",
    "@playwright/test": "^1.50.0",
    "eslint": "^9.0.0",
    "prettier": "^3.4.0"
  }
}
```

### Backend (`requirements.txt`)

```
# === Web Framework ===
fastapi>=0.128.0
uvicorn[standard]>=0.34.0
pydantic>=2.10.0
python-multipart>=0.0.18
python-jose[cryptography]>=3.3.0

# === Database ===
supabase>=2.12.0
asyncpg>=0.30.0
sqlalchemy>=2.0.36

# === HTTP Client ===
httpx>=0.28.0

# === Task Queue ===
celery[redis]>=5.4.0
redis>=5.2.0

# === ML Core ===
numpy>=2.2.0
pandas>=2.2.0
scipy>=1.15.0
scikit-learn>=1.7.0
torch>=2.8.0
optuna>=4.7.0

# === ML Utilities ===
shap>=0.46.0
dtaidistance>=2.3.0
joblib>=1.4.0

# === LLM / Conversational AI ===
langchain>=0.3.14
langgraph>=1.0.0
langgraph-checkpoint-postgres>=2.0.0
langchain-openai>=0.3.0
langchain-anthropic>=0.3.0
openai>=1.58.0
tiktoken>=0.8.0

# === Wearable Data Parsing ===
fitparse>=0.6.0
gpxpy>=1.6.0

# === Monitoring ===
sentry-sdk[fastapi]>=2.19.0

# === Testing ===
pytest>=8.3.0
pytest-asyncio>=0.25.0
pytest-cov>=6.0.0
```

---

## Appendix A: Key Architectural Decisions Record (ADR)

### ADR-001: Next.js PWA over React Native

**Decision**: Build a Progressive Web App with thin native wrappers instead of React Native.
**Rationale**: Single codebase for web + mobile. Native wrappers only needed for HealthKit and Health Connect — everything else (Garmin, Strava, Fitbit) uses web APIs. PWA reduces development cost by ~60% vs maintaining separate native apps.

### ADR-002: FastAPI over Django for ML Backend

**Decision**: FastAPI as the Python backend instead of Django.
**Rationale**: Async-first design for concurrent wearable API calls. First-class Pydantic integration for ML data validation. Lighter weight — no ORM needed since Supabase handles data layer. Native WebSocket support for chat streaming.

### ADR-003: Supabase over AWS for Database/Auth

**Decision**: Supabase as the primary data platform.
**Rationale**: Managed Postgres with pgvector eliminates need for separate vector DB (Pinecone/Weaviate). Built-in auth, RLS, realtime, and edge functions reduce infrastructure complexity. Supabase Storage for FIT files avoids S3 configuration. Developer experience optimized for the Next.js + Python stack.

### ADR-004: LangGraph over Raw LangChain for Chat Agent

**Decision**: LangGraph stateful agent instead of raw LangChain chains.
**Rationale**: PIRX chat needs stateful conversations with memory (PostgresSaver checkpointing). Agent graph supports conditional routing (projection queries vs training analysis vs general chat). Built-in human-in-the-loop for future coach-review workflows. Production-ready deployment with streaming.

### ADR-005: Terra API as Wearable Aggregation Layer

**Decision**: Terra API as default wearable integration with direct API overrides for key platforms.
**Rationale**: Covers 500+ devices with one integration. Handles OAuth complexity for minor platforms. Direct APIs for Garmin, Strava, Fitbit give deeper data (FIT files, interval splits) that Terra may not expose. Hybrid approach balances coverage with depth.

### ADR-006: Per-Runner Models over Global Model

**Decision**: Train individual LSTM models per user instead of one global model.
**Rationale**: Research (Dash 2024) shows 15 individual LSTMs outperform a single global network. Aligns with PIRX's Structural Identity concept. Each runner's physiology is unique — global models smooth over individual patterns. Compute cost is acceptable since models are small (17 neurons) and retrain weekly.

### ADR-007: Huber Loss over MSE for All Regression

**Decision**: Use Huber loss instead of Mean Squared Error for all time-prediction models.
**Rationale**: Running data inherently contains outliers (GPS errors, mislabeled activities, anomalous sessions). Huber loss is robust to these outliers while still being differentiable. Validated in Dash (2024) as superior to MSE for this domain.

---

## Appendix B: Data Flow — Activity Sync to Projection Update

```
Wearable Device
     │
     ▼
Garmin/Strava/Fitbit webhook → Supabase Edge Function
     │
     ▼
Validate webhook signature → Store raw activity in `activities` table
     │
     ▼
Trigger Celery task: `feature_engineering`
     │
     ▼
Data cleaning pipeline (Dash 2024):
  - Filter runs only
  - Remove < 3 min, < 1.6 km
  - Remove pace outliers (slower than avg, faster than world record)
  - Remove zero elevation/missing data
     │
     ▼
Compute rolling features:
  - 7d, 21d, 42d volume
  - Z1-Z5 distribution
  - Matched HR band pace
  - EWMA acute/chronic load
  - ACWR (4w, 6w, 8w windows)
     │
     ▼
Check structural shift threshold (≥ 2 seconds)
     │
     ├── YES → Trigger `recompute_projection` task
     │           │
     │           ▼
     │         Load per-user model (LSTM / Gradient Boosting)
     │           │
     │           ▼
     │         Compute new driver states (5 drivers sum to total)
     │           │
     │           ▼
     │         Apply volatility dampening (α smoothing)
     │           │
     │           ▼
     │         Store new Projection_State and Driver_State
     │           │
     │           ▼
     │         Generate embedding for projection change
     │           │
     │           ▼
     │         Supabase Realtime → Frontend updates instantly
     │
     └── NO → Update feature cache only (no projection change)
```

---

## Appendix C: Phase Roadmap

### Phase 1: Foundation (Weeks 1-8)
- [ ] Supabase project setup (schema, RLS, auth)
- [ ] Next.js PWA scaffolding with shadcn/ui
- [ ] FastAPI backend with core endpoints
- [ ] Strava + Garmin integration (direct APIs)
- [ ] LMC rank 2 projection from race data
- [ ] Basic projection display (midpoint + range)

### Phase 2: Intelligence (Weeks 9-16)
- [ ] Feature engineering pipeline
- [ ] KNN similar-runner seeding
- [ ] Driver attribution model
- [ ] Event Readiness scoring
- [ ] Terra API integration (expand wearable support)
- [ ] Push notifications (6 core triggers)

### Phase 3: AI-Native (Weeks 17-24)
- [ ] LangGraph chat agent
- [ ] RAG pipeline (embeddings + vector search)
- [ ] Per-user LSTM model training
- [ ] SHAP-based driver explanations
- [ ] "What We're Learning About You" module
- [ ] iOS/Android native wrappers (HealthKit + Health Connect)

### Phase 4: Scale (Weeks 25-32)
- [ ] Social layer (shareable Race Prediction Cards)
- [ ] Coach Dashboard (B2B)
- [ ] Adjunct Analysis module
- [ ] Diagnostic Lab API integration
- [ ] Advanced pacing recommendations (CBR)
- [ ] Model accuracy framework (public benchmark)
