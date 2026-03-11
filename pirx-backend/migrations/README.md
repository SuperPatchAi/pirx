# PIRX Database Migrations

Run these SQL files against your Supabase PostgreSQL database in numeric order.

## Canonical Migration Order

1. `001_initial_schema.sql` - Base tables, indexes, and extensions
2. `002_rls_policies.sql` - Row Level Security policies
3. `003_realtime.sql` - Realtime publication/subscription setup
4. `004_functions.sql` - Database functions and triggers
5. `005_schema_alignment.sql` - Schema alignment for projection/pipeline fields
6. `006_chat_threads.sql` - Chat thread/message schema
7. `007_chat_rls.sql` - Chat-specific RLS policies
8. `008_push_subscriptions.sql` - Push subscription storage
9. `009_cohort_benchmarks.sql` - Cohort benchmark and social comparison tables
10. `010_coach_dashboard.sql` - Coach/athlete dashboard schema
11. `011_missing_indexes.sql` - Additional performance indexes
12. `012_model_metrics_alignment.sql` - Align model metrics schema with task/API payloads
13. `013_ml_lifecycle.sql` - Model registry, training jobs, artifacts, Optuna, and injury-risk assessment tables
14. `014_projection_model_metadata.sql` - Projection model type extension and fallback reason field

## How to Run (psql)

Execute from `pirx-backend`:

```bash
psql "$SUPABASE_DB_URL" -f migrations/001_initial_schema.sql
psql "$SUPABASE_DB_URL" -f migrations/002_rls_policies.sql
psql "$SUPABASE_DB_URL" -f migrations/003_realtime.sql
psql "$SUPABASE_DB_URL" -f migrations/004_functions.sql
psql "$SUPABASE_DB_URL" -f migrations/005_schema_alignment.sql
psql "$SUPABASE_DB_URL" -f migrations/006_chat_threads.sql
psql "$SUPABASE_DB_URL" -f migrations/007_chat_rls.sql
psql "$SUPABASE_DB_URL" -f migrations/008_push_subscriptions.sql
psql "$SUPABASE_DB_URL" -f migrations/009_cohort_benchmarks.sql
psql "$SUPABASE_DB_URL" -f migrations/010_coach_dashboard.sql
psql "$SUPABASE_DB_URL" -f migrations/011_missing_indexes.sql
psql "$SUPABASE_DB_URL" -f migrations/012_model_metrics_alignment.sql
psql "$SUPABASE_DB_URL" -f migrations/013_ml_lifecycle.sql
psql "$SUPABASE_DB_URL" -f migrations/014_projection_model_metadata.sql
```

## Notes

- These migrations are additive and should be run in order.
- If onboarding a new environment, verify all 14 migrations are applied before running backend workers.

## README Delta - `012_model_metrics_alignment.sql`

- **What changed**: Added migration `012_model_metrics_alignment.sql` to align `model_metrics` with current task writers and API readers.
- **Why it changed**: Prevent runtime insert failures from schema/task contract drift (`global`, `event_*`, and bias-correction payload fields).
- **Code touchpoints**: `pirx-backend/migrations/012_model_metrics_alignment.sql`, `supabase/migrations/20260311000004_model_metrics_alignment.sql`, `pirx-backend/app/tasks/projection_tasks.py`.
- **Data-flow impact**: Projection/accuracy task stage only (metric logging and observability).
- **Formula/constant changes**: none.
- **API/schema impact**: `model_metrics` now supports `metric_type`, `event`, `actual_seconds`, `projected_seconds`, `race_timestamp`, `computed_at`, and expanded `model_type` constraint.
- **Verification**: Ran targeted backend test `tests/test_tasks.py::TestBiasCorrectionDetailed::test_bias_correction_logs_metric` using project venv; passed.

## README Delta - `013_ml_lifecycle.sql`

- **What changed**: Added model lifecycle schema (`model_registry`, `model_training_jobs`, `optuna_studies`, `optuna_trials`, `model_artifacts`, `injury_risk_assessments`).
- **Why it changed**: Provide production persistence contracts for phased LSTM/KNN/Optuna/RF rollout and auditability.
- **Code touchpoints**: `pirx-backend/migrations/013_ml_lifecycle.sql`, `supabase/migrations/20260311000005_ml_lifecycle.sql`, `pirx-backend/app/tasks/ml_tasks.py`, `pirx-backend/app/ml/injury_risk_model.py`.
- **Data-flow impact**: ML training/tuning/serving observability and injury-risk persistence stages.
- **Formula/constant changes**: none.
- **API/schema impact**: New additive tables and indexes; no breaking change to existing projection/readiness endpoints.
- **Verification**: Backend tests pass after schema addition and API/task integration updates.

## README Delta - `014_projection_model_metadata.sql`

- **What changed**: Added `fallback_reason` to `projection_state` and expanded `projection_state.model_type` constraint to include `deterministic`.
- **Why it changed**: Persist deterministic fallback provenance while model orchestrator begins selecting candidate ML families during phased rollout.
- **Code touchpoints**: `pirx-backend/migrations/014_projection_model_metadata.sql`, `supabase/migrations/20260311000006_projection_model_metadata.sql`, `pirx-backend/app/services/projection_service.py`, `pirx-backend/app/services/driver_service.py`.
- **Data-flow impact**: Projection write/read metadata path only.
- **Formula/constant changes**: none.
- **API/schema impact**: Additive projection metadata; existing `/projection` and `/projection/all` contracts remain backward compatible.
- **Verification**: Ran targeted suite including `tests/test_projection_endpoints.py` and `tests/test_services_wiring.py`; passing.
