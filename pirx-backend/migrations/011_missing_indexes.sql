-- Migration 011: Add missing indexes for beta scalability
-- These tables lacked user_id or lookup indexes, causing full scans at scale.

CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user ON push_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_adjunct_state_user ON adjunct_state(user_id);
CREATE INDEX IF NOT EXISTS idx_model_metrics_type_date ON model_metrics(model_type, metric_date DESC);
