# PIRX Database Migrations

Run these SQL files against your Supabase PostgreSQL database in order.

## Migration Order
1. `001_initial_schema.sql` — Tables, indexes, extensions
2. `002_rls_policies.sql` — Row Level Security policies
3. `003_realtime.sql` — Supabase Realtime subscriptions
4. `004_functions.sql` — Database functions and triggers

## How to Run
Execute via Supabase SQL Editor or psql:
```bash
psql $SUPABASE_DB_URL -f migrations/001_initial_schema.sql
psql $SUPABASE_DB_URL -f migrations/002_rls_policies.sql
psql $SUPABASE_DB_URL -f migrations/003_realtime.sql
psql $SUPABASE_DB_URL -f migrations/004_functions.sql
```
