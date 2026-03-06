-- RLS policies for chat_threads and chat_messages.
-- These tables have RLS enabled in 006 but no policies, blocking all access.

CREATE POLICY "Users can view own chat threads" ON chat_threads
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own chat threads" ON chat_threads
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own chat threads" ON chat_threads
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own chat threads" ON chat_threads
    FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own chat messages" ON chat_messages
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM chat_threads WHERE thread_id = chat_messages.thread_id AND user_id = auth.uid())
    );
CREATE POLICY "Users can insert own chat messages" ON chat_messages
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM chat_threads WHERE thread_id = chat_messages.thread_id AND user_id = auth.uid())
    );
