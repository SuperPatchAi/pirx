-- 20260311000005_ml_lifecycle.sql
-- Model lifecycle schema for personalized ML rollout.

CREATE TABLE IF NOT EXISTS model_registry (
    model_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    event TEXT,
    model_family TEXT NOT NULL CHECK (model_family IN ('deterministic', 'lstm', 'knn', 'lmc', 'gradient_boosting', 'random_forest')),
    version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('training', 'active', 'inactive', 'failed', 'archived')),
    feature_schema_hash TEXT,
    training_window_start TIMESTAMPTZ,
    training_window_end TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_model_registry_user_event
    ON model_registry(user_id, event, created_at DESC);

CREATE TABLE IF NOT EXISTS model_training_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES model_registry(model_id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    job_type TEXT NOT NULL CHECK (job_type IN ('lstm_train', 'optuna_tune', 'rf_train', 'knn_refresh')),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    celery_task_id TEXT,
    trigger_source TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_model_training_jobs_user
    ON model_training_jobs(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS optuna_studies (
    study_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES model_training_jobs(job_id) ON DELETE CASCADE,
    model_id UUID REFERENCES model_registry(model_id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    study_name TEXT NOT NULL,
    direction TEXT NOT NULL DEFAULT 'minimize' CHECK (direction IN ('minimize', 'maximize')),
    best_value FLOAT,
    best_trial_number INTEGER,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_optuna_studies_user
    ON optuna_studies(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS optuna_trials (
    trial_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    study_id UUID REFERENCES optuna_studies(study_id) ON DELETE CASCADE NOT NULL,
    trial_number INTEGER NOT NULL,
    state TEXT NOT NULL,
    value FLOAT,
    params JSONB,
    attributes JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(study_id, trial_number)
);

CREATE TABLE IF NOT EXISTS model_artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID REFERENCES model_registry(model_id) ON DELETE CASCADE NOT NULL,
    job_id UUID REFERENCES model_training_jobs(job_id) ON DELETE SET NULL,
    artifact_type TEXT NOT NULL CHECK (artifact_type IN ('weights', 'preprocessor', 'config', 'metrics')),
    storage_uri TEXT NOT NULL,
    checksum TEXT,
    size_bytes BIGINT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_model_artifacts_model
    ON model_artifacts(model_id, created_at DESC);

CREATE TABLE IF NOT EXISTS injury_risk_assessments (
    assessment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    event TEXT,
    model_id UUID REFERENCES model_registry(model_id) ON DELETE SET NULL,
    risk_probability FLOAT NOT NULL CHECK (risk_probability >= 0 AND risk_probability <= 1),
    risk_band TEXT NOT NULL CHECK (risk_band IN ('low', 'moderate', 'high')),
    feature_contributions JSONB,
    computed_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_injury_risk_user_event
    ON injury_risk_assessments(user_id, event, computed_at DESC);
