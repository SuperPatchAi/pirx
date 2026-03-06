-- PIRX Supabase Realtime Subscriptions
-- Enable realtime on tables the frontend subscribes to for live updates.

ALTER PUBLICATION supabase_realtime ADD TABLE projection_state;
ALTER PUBLICATION supabase_realtime ADD TABLE driver_state;
ALTER PUBLICATION supabase_realtime ADD TABLE task_registry;
ALTER PUBLICATION supabase_realtime ADD TABLE notification_log;
