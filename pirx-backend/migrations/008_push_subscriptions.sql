CREATE TABLE IF NOT EXISTS push_subscriptions (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    endpoint TEXT NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, endpoint)
);

ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own subscriptions" ON push_subscriptions
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own subscriptions" ON push_subscriptions
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete own subscriptions" ON push_subscriptions
    FOR DELETE USING (auth.uid() = user_id);
