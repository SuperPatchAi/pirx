-- PIRX Initial Schema Migration
-- Creates all core tables, indexes, and triggers for the PIRX running performance intelligence app.

-- ============================================================================
-- 1. Extensions
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- ============================================================================
-- 2. Users
-- ============================================================================

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    primary_event TEXT DEFAULT '3000' CHECK (primary_event IN ('1500', '3000', '5000', '10000')),
    baseline_event_id UUID,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- 3. Activities
-- ============================================================================

CREATE TABLE activities (
    activity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    external_id TEXT,
    source TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    duration_seconds INTEGER NOT NULL,
    distance_meters FLOAT NOT NULL,
    avg_hr INTEGER,
    max_hr INTEGER,
    avg_pace_sec_per_km FLOAT,
    elevation_gain_m FLOAT,
    calories INTEGER,
    activity_type TEXT NOT NULL CHECK (activity_type IN ('easy', 'threshold', 'interval', 'race', 'cross-training', 'unknown')),
    hr_zones FLOAT[],
    laps JSONB,
    adjunct_tags TEXT[],
    fit_file_url TEXT,
    raw_data JSONB,
    is_cleaned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, external_id, source)
);

CREATE INDEX idx_activities_user_timestamp ON activities(user_id, timestamp DESC);
CREATE INDEX idx_activities_user_type ON activities(user_id, activity_type);

-- ============================================================================
-- 4. Intervals
-- ============================================================================

CREATE TABLE intervals (
    interval_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_id UUID REFERENCES activities(activity_id) ON DELETE CASCADE NOT NULL,
    interval_number INTEGER NOT NULL,
    duration_seconds INTEGER NOT NULL,
    distance_meters FLOAT,
    avg_pace_sec_per_km FLOAT,
    avg_hr INTEGER,
    max_hr INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_intervals_activity ON intervals(activity_id);

-- ============================================================================
-- 5. Projection State (immutable, append-only)
-- ============================================================================

CREATE TABLE projection_state (
    projection_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    event TEXT NOT NULL CHECK (event IN ('1500', '3000', '5000', '10000')),
    midpoint_seconds FLOAT NOT NULL,
    range_lower FLOAT NOT NULL,
    range_upper FLOAT NOT NULL,
    confidence_score FLOAT NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    volatility_score FLOAT NOT NULL CHECK (volatility_score >= 0),
    improvement_since_baseline FLOAT DEFAULT 0,
    twenty_one_day_change FLOAT DEFAULT 0,
    status TEXT DEFAULT 'Holding' CHECK (status IN ('Holding', 'Improving', 'Declining', 'Projection Adjusted', 'Updated Based on Recent Race')),
    model_type TEXT DEFAULT 'lmc' CHECK (model_type IN ('lmc', 'knn', 'lstm', 'gradient_boosting')),
    computed_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_projection_user_event ON projection_state(user_id, event, computed_at DESC);

-- ============================================================================
-- 6. Driver State (linked to projection)
-- ============================================================================

CREATE TABLE driver_state (
    driver_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    projection_id UUID REFERENCES projection_state(projection_id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    aerobic_base_seconds FLOAT NOT NULL DEFAULT 0,
    threshold_density_seconds FLOAT NOT NULL DEFAULT 0,
    speed_exposure_seconds FLOAT NOT NULL DEFAULT 0,
    load_consistency_seconds FLOAT NOT NULL DEFAULT 0,
    running_economy_seconds FLOAT NOT NULL DEFAULT 0,
    computed_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT drivers_sum_check CHECK (
        ABS(
            aerobic_base_seconds + threshold_density_seconds + speed_exposure_seconds
            + load_consistency_seconds + running_economy_seconds
        ) >= 0
    )
);

CREATE INDEX idx_driver_state_user ON driver_state(user_id, computed_at DESC);

-- ============================================================================
-- 7. Physiology
-- ============================================================================

CREATE TABLE physiology (
    entry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT now(),
    source TEXT DEFAULT 'manual' CHECK (source IN ('manual', 'wearable')),
    resting_hr INTEGER,
    hrv FLOAT,
    sleep_score FLOAT,
    confidence_score FLOAT CHECK (confidence_score IS NULL OR (confidence_score >= 1 AND confidence_score <= 10)),
    fatigue_score FLOAT CHECK (fatigue_score IS NULL OR (fatigue_score >= 1 AND fatigue_score <= 10)),
    focus_score FLOAT CHECK (focus_score IS NULL OR (focus_score >= 1 AND focus_score <= 10)),
    notes TEXT,
    blood_lactate_rest FLOAT,
    blood_lactate_easy FLOAT,
    blood_lactate_threshold FLOAT,
    blood_lactate_race FLOAT,
    hemoglobin FLOAT,
    hematocrit FLOAT,
    ferritin FLOAT,
    rbc FLOAT,
    iron FLOAT,
    vitamin_d FLOAT,
    testosterone FLOAT,
    custom_fields JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_physiology_user_timestamp ON physiology(user_id, timestamp DESC);

-- ============================================================================
-- 8. Adjunct State
-- ============================================================================

CREATE TABLE adjunct_state (
    adjunct_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    adjunct_name TEXT NOT NULL,
    sessions_analyzed INTEGER DEFAULT 0,
    median_projection_delta FLOAT,
    hr_drift_delta FLOAT,
    volatility_delta FLOAT,
    statistical_status TEXT DEFAULT 'observational' CHECK (statistical_status IN ('observational', 'emerging', 'supported')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, adjunct_name)
);

-- ============================================================================
-- 9. Activity-Adjunct Junction
-- ============================================================================

CREATE TABLE activity_adjuncts (
    activity_id UUID REFERENCES activities(activity_id) ON DELETE CASCADE NOT NULL,
    adjunct_id UUID REFERENCES adjunct_state(adjunct_id) ON DELETE CASCADE NOT NULL,
    PRIMARY KEY (activity_id, adjunct_id)
);

-- ============================================================================
-- 10. Wearable Connections
-- ============================================================================

CREATE TABLE wearable_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    provider TEXT NOT NULL,
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,
    terra_user_id TEXT,
    scopes TEXT[],
    connected_at TIMESTAMPTZ DEFAULT now(),
    last_sync_at TIMESTAMPTZ,
    sync_status TEXT DEFAULT 'connected' CHECK (sync_status IN ('connected', 'syncing', 'error', 'disconnected')),
    UNIQUE(user_id, provider)
);

CREATE INDEX idx_wearable_user ON wearable_connections(user_id);

-- ============================================================================
-- 11. User Embeddings (Chat RAG)
-- ============================================================================

CREATE TABLE user_embeddings (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    content_type TEXT NOT NULL CHECK (content_type IN ('activity_summary', 'projection_change', 'insight', 'driver_shift')),
    content TEXT NOT NULL,
    metadata JSONB,
    embedding extensions.vector(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_embeddings_user ON user_embeddings(user_id);
CREATE INDEX idx_embeddings_vector ON user_embeddings USING hnsw (embedding extensions.vector_cosine_ops);

-- ============================================================================
-- 12. Model Metrics (observability)
-- ============================================================================

CREATE TABLE model_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    model_type TEXT NOT NULL CHECK (model_type IN ('lstm', 'knn', 'lmc', 'gradient_boosting')),
    mae_seconds FLOAT,
    bias_seconds FLOAT,
    bland_altman_lower FLOAT,
    bland_altman_upper FLOAT,
    cohens_d FLOAT,
    sample_size INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- 13. Notification Log
-- ============================================================================

CREATE TABLE notification_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    notification_type TEXT NOT NULL CHECK (notification_type IN ('projection_update', 'readiness_shift', 'intervention', 'weekly_summary', 'race_approaching', 'new_insight')),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    delivered_at TIMESTAMPTZ DEFAULT now(),
    read_at TIMESTAMPTZ,
    deep_link TEXT
);

CREATE INDEX idx_notification_user ON notification_log(user_id, delivered_at DESC);

-- ============================================================================
-- 14. Task Registry (Celery task tracking)
-- ============================================================================

CREATE TABLE task_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    task_name TEXT NOT NULL,
    task_id TEXT NOT NULL,
    status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    queued_at TIMESTAMPTZ DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB
);

CREATE INDEX idx_task_user ON task_registry(user_id, queued_at DESC);

-- ============================================================================
-- 15. Updated_at Trigger Function
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_adjunct_state_updated_at BEFORE UPDATE ON adjunct_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
