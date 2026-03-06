-- 005_schema_alignment.sql
-- Align database schema with application code expectations.
-- Adds missing columns, widens CHECK constraints, makes nullable columns where needed.

-- A1: projection_state alignment
ALTER TABLE projection_state ADD COLUMN IF NOT EXISTS range_low_seconds FLOAT;
ALTER TABLE projection_state ADD COLUMN IF NOT EXISTS range_high_seconds FLOAT;
ALTER TABLE projection_state ADD COLUMN IF NOT EXISTS baseline_seconds FLOAT;
ALTER TABLE projection_state ADD COLUMN IF NOT EXISTS volatility FLOAT;
ALTER TABLE projection_state DROP CONSTRAINT IF EXISTS projection_state_event_check;
ALTER TABLE projection_state ADD CONSTRAINT projection_state_event_check
  CHECK (event IN ('1500', '3000', '5000', '10000', '21097', '42195'));

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

-- A3: activities alignment
ALTER TABLE activities ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
UPDATE activities SET started_at = timestamp WHERE started_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_activities_user_started ON activities(user_id, started_at DESC);
ALTER TABLE activities DROP CONSTRAINT IF EXISTS activities_activity_type_check;
ALTER TABLE activities ADD CONSTRAINT activities_activity_type_check
  CHECK (activity_type IN ('easy', 'threshold', 'interval', 'race', 'cross-training', 'unknown', 'long_run', 'tempo'));

-- A4: users alignment
ALTER TABLE users ADD COLUMN IF NOT EXISTS baseline_event TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS baseline_time_seconds FLOAT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS baseline_race_date DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS baseline_source TEXT DEFAULT 'auto';
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_primary_event_check;
ALTER TABLE users ADD CONSTRAINT users_primary_event_check
  CHECK (primary_event IN ('1500', '3000', '5000', '10000', '21097', '42195'));

-- A5: wearable_connections alignment
ALTER TABLE wearable_connections ADD COLUMN IF NOT EXISTS access_token TEXT;
ALTER TABLE wearable_connections ADD COLUMN IF NOT EXISTS refresh_token TEXT;
ALTER TABLE wearable_connections ADD COLUMN IF NOT EXISTS athlete_id TEXT;
ALTER TABLE wearable_connections ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- A6: users custom_fields for preferences
ALTER TABLE users ADD COLUMN IF NOT EXISTS custom_fields JSONB DEFAULT '{}';
