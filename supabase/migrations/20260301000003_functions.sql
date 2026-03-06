-- PIRX Database Functions and Triggers
-- RAG embedding search, projection helpers, and driver sum validation.

-- ============================================================================
-- Query similar embeddings for Chat RAG
-- ============================================================================

CREATE OR REPLACE FUNCTION query_embeddings(
    query_embedding extensions.vector(1536),
    match_user_id UUID,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    content_type TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ue.id,
        ue.content,
        ue.content_type,
        ue.metadata,
        1 - (ue.embedding <=> query_embedding) as similarity
    FROM user_embeddings ue
    WHERE ue.user_id = match_user_id
    ORDER BY ue.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================================================
-- Get latest projection for a user + event
-- ============================================================================

CREATE OR REPLACE FUNCTION get_latest_projection(
    p_user_id UUID,
    p_event TEXT
)
RETURNS projection_state
LANGUAGE plpgsql
AS $$
DECLARE
    result projection_state;
BEGIN
    SELECT * INTO result
    FROM projection_state
    WHERE user_id = p_user_id AND event = p_event
    ORDER BY computed_at DESC
    LIMIT 1;
    RETURN result;
END;
$$;

-- ============================================================================
-- Driver sum validation trigger
-- Ensures the five driver contributions sum to the projection improvement.
-- ============================================================================

CREATE OR REPLACE FUNCTION validate_driver_sum()
RETURNS TRIGGER AS $$
DECLARE
    proj_improvement FLOAT;
    driver_sum FLOAT;
BEGIN
    SELECT improvement_since_baseline INTO proj_improvement
    FROM projection_state
    WHERE projection_id = NEW.projection_id;

    driver_sum := NEW.aerobic_base_seconds + NEW.threshold_density_seconds
                  + NEW.speed_exposure_seconds + NEW.load_consistency_seconds
                  + NEW.running_economy_seconds;

    IF ABS(driver_sum - proj_improvement) > 0.01 THEN
        RAISE EXCEPTION 'Driver sum (%) does not equal projection improvement (%)', driver_sum, proj_improvement;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_driver_sum
    BEFORE INSERT ON driver_state
    FOR EACH ROW EXECUTE FUNCTION validate_driver_sum();
