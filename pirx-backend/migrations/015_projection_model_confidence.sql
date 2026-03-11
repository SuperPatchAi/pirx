-- Ensure projection_state supports model confidence metadata persisted by serving path.
ALTER TABLE IF EXISTS public.projection_state
  ADD COLUMN IF NOT EXISTS model_confidence DOUBLE PRECISION;
