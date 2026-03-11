-- 20260311000006_projection_model_metadata.sql
-- Extend projection_state model metadata support.

ALTER TABLE projection_state
    ADD COLUMN IF NOT EXISTS fallback_reason TEXT;

ALTER TABLE projection_state
    DROP CONSTRAINT IF EXISTS projection_state_model_type_check;

ALTER TABLE projection_state
    ADD CONSTRAINT projection_state_model_type_check
    CHECK (
        model_type IN ('deterministic', 'lmc', 'knn', 'lstm', 'gradient_boosting')
    );
