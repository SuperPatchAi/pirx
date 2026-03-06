-- PIRX Row Level Security Policies
-- Every table gets RLS enabled. Users can only access their own data.
-- Projection and driver state are read-only for users (service role inserts).

-- ============================================================================
-- Enable RLS on ALL tables
-- ============================================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE intervals ENABLE ROW LEVEL SECURITY;
ALTER TABLE projection_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE driver_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE physiology ENABLE ROW LEVEL SECURITY;
ALTER TABLE adjunct_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_adjuncts ENABLE ROW LEVEL SECURITY;
ALTER TABLE wearable_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_registry ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Users: read/update own profile
-- ============================================================================

CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid() = user_id);

-- ============================================================================
-- Activities: full CRUD on own data
-- ============================================================================

CREATE POLICY "Users can view own activities" ON activities
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own activities" ON activities
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete own activities" ON activities
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================================
-- Intervals: read own via activity ownership
-- ============================================================================

CREATE POLICY "Users can view own intervals" ON intervals
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM activities WHERE activity_id = intervals.activity_id AND user_id = auth.uid())
    );

-- ============================================================================
-- Projection State: read-only for users (service role inserts)
-- ============================================================================

CREATE POLICY "Users can view own projections" ON projection_state
    FOR SELECT USING (auth.uid() = user_id);

-- ============================================================================
-- Driver State: read-only for users (service role inserts)
-- ============================================================================

CREATE POLICY "Users can view own drivers" ON driver_state
    FOR SELECT USING (auth.uid() = user_id);

-- ============================================================================
-- Physiology: full CRUD on own data
-- ============================================================================

CREATE POLICY "Users can view own physiology" ON physiology
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own physiology" ON physiology
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own physiology" ON physiology
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own physiology" ON physiology
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================================
-- Adjunct State: full CRUD on own data
-- ============================================================================

CREATE POLICY "Users can view own adjuncts" ON adjunct_state
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own adjuncts" ON adjunct_state
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own adjuncts" ON adjunct_state
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own adjuncts" ON adjunct_state
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================================
-- Activity Adjuncts: access via activity ownership
-- ============================================================================

CREATE POLICY "Users can view own activity adjuncts" ON activity_adjuncts
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM activities WHERE activity_id = activity_adjuncts.activity_id AND user_id = auth.uid())
    );
CREATE POLICY "Users can insert own activity adjuncts" ON activity_adjuncts
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM activities WHERE activity_id = activity_adjuncts.activity_id AND user_id = auth.uid())
    );

-- ============================================================================
-- Wearable Connections: full CRUD on own data
-- ============================================================================

CREATE POLICY "Users can view own connections" ON wearable_connections
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own connections" ON wearable_connections
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own connections" ON wearable_connections
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own connections" ON wearable_connections
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================================
-- User Embeddings: read-only for users (service role inserts)
-- ============================================================================

CREATE POLICY "Users can view own embeddings" ON user_embeddings
    FOR SELECT USING (auth.uid() = user_id);

-- ============================================================================
-- Model Metrics: read-only for users
-- ============================================================================

CREATE POLICY "Users can view own metrics" ON model_metrics
    FOR SELECT USING (auth.uid() = user_id);

-- ============================================================================
-- Notification Log: read/update own (mark as read)
-- ============================================================================

CREATE POLICY "Users can view own notifications" ON notification_log
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own notifications" ON notification_log
    FOR UPDATE USING (auth.uid() = user_id);

-- ============================================================================
-- Task Registry: read-only for users
-- ============================================================================

CREATE POLICY "Users can view own tasks" ON task_registry
    FOR SELECT USING (auth.uid() = user_id);
