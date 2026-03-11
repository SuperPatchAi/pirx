-- 20260311000004_model_metrics_alignment.sql
-- Align model_metrics schema with current task payloads and API usage.

ALTER TABLE model_metrics
    ADD COLUMN IF NOT EXISTS metric_type TEXT,
    ADD COLUMN IF NOT EXISTS event TEXT,
    ADD COLUMN IF NOT EXISTS actual_seconds FLOAT,
    ADD COLUMN IF NOT EXISTS projected_seconds FLOAT,
    ADD COLUMN IF NOT EXISTS race_timestamp TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS computed_at TIMESTAMPTZ DEFAULT now();

ALTER TABLE model_metrics
    DROP CONSTRAINT IF EXISTS model_metrics_model_type_check;

ALTER TABLE model_metrics
    ADD CONSTRAINT model_metrics_model_type_check
    CHECK (
        model_type IN ('lstm', 'knn', 'lmc', 'gradient_boosting', 'global')
        OR model_type ~ '^event_[0-9]+$'
    );

CREATE INDEX IF NOT EXISTS idx_model_metrics_metric_type_date
    ON model_metrics(metric_type, metric_date DESC);

CREATE INDEX IF NOT EXISTS idx_model_metrics_event_date
    ON model_metrics(event, metric_date DESC);
