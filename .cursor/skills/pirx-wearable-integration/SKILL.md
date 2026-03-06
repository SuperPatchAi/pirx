---
name: pirx-wearable-integration
description: Wearable data integration patterns for PIRX running performance app. Covers Garmin, Strava, Apple Health, Google Fit, Fitbit, Suunto, COROS, WHOOP, Oura, and Polar via Terra API aggregation and direct APIs. Includes webhook handling, OAuth token storage, FIT file parsing, normalized activity schema, data sync flow, and activity type classification.
---

# PIRX Wearable Data Integration

## PIRX Context

PIRX is a running performance prediction app. It needs wearable data from running watches and fitness trackers to feed its projection engine. The projection engine computes a **Projected Time** for race distances based on training data.

## Hybrid Strategy: Terra + Direct APIs

Three integration tiers:

1. **Terra API** (`tryterra.co`) — default aggregation layer covering 150+ devices with unified JSON schema
2. **Direct API integrations** — deeper data access for: Garmin Health API, Strava API, Fitbit Web API
3. **Platform-specific native bridges** — Apple HealthKit (iOS native, no REST API), Google Health Connect (Android native, Google Fit REST deprecated 2026)

## Platform Matrix

| Platform | Method | Data | Auth |
|---|---|---|---|
| Garmin | Terra + Garmin Health API (direct) | HR, HRV, sleep, stress, activities, FIT files | OAuth 2.0 via Garmin Connect |
| Strava | Direct API | Activities, GPS tracks, segments, efforts | OAuth 2.0 (webhook subscription) |
| Apple Health | iOS native bridge → backend | All HealthKit data types | On-device permission |
| Google Health Connect | Android native bridge → backend | All Health Connect data types | On-device permission |
| Fitbit | Terra + Fitbit Web API (direct) | HR, sleep, activities, SpO2 | OAuth 2.0 PKCE |
| Suunto | Terra + Suunto Cloud API | FIT files, HR, GPS, altitude | OAuth 2.0 via Suunto API Zone |
| COROS | Terra + COROS Open API | Activities, HR, GPS, FIT files | OAuth 2.0 partner program |
| WHOOP | Terra API | Strain, recovery, sleep, HRV | OAuth 2.0 |
| Oura | Terra API | Sleep, readiness, HRV, temperature | OAuth 2.0 |
| Polar | Terra API | HR, activities, sleep, Orthostatic test | OAuth 2.0 |

## Terra API Integration Pattern

- **Base URL**: `https://api.tryterra.co/v2`
- **Auth headers**: `x-api-key` + `dev-id`
- **User connection**: Terra widget session via `POST /auth/generateWidgetSession` with `reference_id`, `auth_success_redirect_url`, `auth_failure_redirect_url`
- **Data endpoints**: `/activity`, `/daily`, `/sleep`, `/body`
- **Data delivery**: Webhooks (push) + REST GET (pull for historical, async for >28 days)

### Webhook Handler (FastAPI)

```python
from fastapi import FastAPI, Request
import os

app = FastAPI()

TERRA_API_URL = "https://api.tryterra.co/v2"

@app.post("/webhook/terra")
async def terra_webhook(request: Request):
    payload = await request.json()
    user_id = payload.get("user", {}).get("user_id")
    data_type = payload["type"]
    # Route: auth, activity, sleep, body, daily
    if data_type == "auth" and payload.get("status") == "success":
        # Trigger historical backfill
        pass
    else:
        # Store data, queue feature engineering
        pass
```

## Strava Direct Integration Pattern

- **OAuth 2.0 scopes**: `activity:read`, `activity:read_all`
- One webhook subscription per app; receives: activity create/update/delete, access revoke
- Webhook POST contains only metadata (`object_id`, `owner_id`, `aspect_type`, `event_time`)
- Must fetch full activity separately via `GET /api/v3/activities/{id}`
- Must respond HTTP 200 within 2 seconds; retries up to 3x on failure

## Normalized Activity Schema

The PIRX canonical format for all wearable data:

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
    'activity_type': str,     # PIRX types: easy, threshold, interval, race, cross-training
    'hr_zones': Optional[List[float]],  # time-in-zone array
    'laps': Optional[List[dict]],       # interval-level data
    'fit_file_url': Optional[str],      # raw FIT file in Supabase Storage
}
```

## Activity Type Classification

Map wearable activity types to PIRX types:

| PIRX Type | Source Activity Types |
|---|---|
| `easy` | recovery run, easy run, jog |
| `threshold` | tempo, threshold run, lactate threshold |
| `interval` | intervals, speed work, fartlek, track |
| `race` | race, competition, virtual race |
| `cross-training` | everything else (cycling, swimming, strength, etc.) |

## Sync Flow

1. User connects wearable (Terra widget or direct OAuth)
2. Historical pull: GET last 6 months of data
3. Webhook registered for ongoing sync
4. On webhook: validate signature → store raw data → queue Celery `feature_engineering` task
5. If structural shift threshold met (≥ 2 seconds) → trigger `recompute_projection`
6. Push realtime update to frontend via Supabase Realtime

## OAuth Token Storage

```sql
CREATE TABLE wearable_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(user_id) NOT NULL,
  provider TEXT NOT NULL,
  access_token_encrypted TEXT,
  refresh_token_encrypted TEXT,
  token_expires_at TIMESTAMPTZ,
  terra_user_id TEXT,
  scopes TEXT[],
  connected_at TIMESTAMPTZ DEFAULT now(),
  last_sync_at TIMESTAMPTZ
);
ALTER TABLE wearable_connections ENABLE ROW LEVEL SECURITY;
```

## FIT File Parsing

- Use `fitparse` for Garmin/Suunto/COROS FIT files
- Use `gpxpy` for GPX files
- Store raw files in Supabase Storage bucket `fit-files`

## Key Dependencies

`httpx`, `fitparse`, `gpxpy`, `cryptography` (webhook signature verification)

## Non-Interference Rule

Wearable sync writes **raw data only**. It never writes to projection state. Only the projection engine writes to projection state.
