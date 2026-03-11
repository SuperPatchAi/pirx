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
```

## Notes

- These migrations are additive and should be run in order.
- If onboarding a new environment, verify all 11 migrations are applied before running backend workers.
