-- PostgreSQL setup script for ArtifactX
-- Run: psql -U postgres -d artifactx -f setup_postgres.sql

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'UTC';

-- Create indexes for performance (run after initial migration)
-- These will be applied automatically on first run

-- Message queries (apply after table creation)
-- CREATE INDEX IF NOT EXISTS ix_wa_messages_timestamp ON wa_messages (timestamp);
-- CREATE INDEX IF NOT EXISTS ix_wa_messages_key_remote_jid ON wa_messages (key_remote_jid);
-- CREATE INDEX IF NOT EXISTS ix_tg_messages_timestamp ON tg_messages (timestamp);
-- CREATE INDEX IF NOT EXISTS ix_tg_messages_dialog_id ON tg_messages (dialog_id);

-- Timeline events
-- CREATE INDEX IF NOT EXISTS ix_timeline_events_normalized_timestamp ON timeline_events (normalized_timestamp);
-- CREATE INDEX IF NOT EXISTS ix_timeline_events_source_app ON timeline_events (source_app);

-- Correlation edges
-- CREATE INDEX IF NOT EXISTS ix_correlation_edges_case_id ON correlation_edges (case_id);

-- Deleted messages
-- CREATE INDEX IF NOT EXISTS ix_deleted_messages_case_id ON deleted_messages (case_id);
-- CREATE INDEX IF NOT EXISTS ix_deleted_messages_source_app ON deleted_messages (source_app);

-- Error logs (high volume table)
-- CREATE INDEX IF NOT EXISTS ix_error_logs_case_id ON error_logs (case_id);
-- CREATE INDEX IF NOT EXISTS ix_error_logs_evidence_id ON error_logs (evidence_id);
-- CREATE INDEX IF NOT EXISTS ix_error_logs_timestamp ON error_logs (timestamp DESC);

-- Function to auto-create indexes on new tables
CREATE OR REPLACE FUNCTION create_performance_indexes()
RETURNS void AS $$
BEGIN
    -- WhatsApp indexes
    CREATE INDEX IF NOT EXISTS ix_wa_messages_timestamp ON wa_messages (timestamp);
    CREATE INDEX IF NOT EXISTS ix_wa_messages_key_remote_jid ON wa_messages (key_remote_jid);
    CREATE INDEX IF NOT EXISTS ix_wa_messages_sender ON wa_messages (sender_jid);

    -- Telegram indexes
    CREATE INDEX IF NOT EXISTS ix_tg_messages_timestamp ON tg_messages (timestamp);
    CREATE INDEX IF NOT EXISTS ix_tg_messages_dialog_id ON tg_messages (dialog_id);
    CREATE INDEX IF NOT EXISTS ix_tg_messages_sender ON tg_messages (sender_id);

    -- Timeline indexes
    CREATE INDEX IF NOT EXISTS ix_timeline_events_normalized_timestamp ON timeline_events (normalized_timestamp);
    CREATE INDEX IF NOT EXISTS ix_timeline_events_source_app ON timeline_events (source_app);

    -- Correlation edges
    CREATE INDEX IF NOT EXISTS ix_correlation_edges_case_id ON correlation_edges (case_id);

    -- Deleted messages
    CREATE INDEX IF NOT EXISTS ix_deleted_messages_case_id ON deleted_messages (case_id);
    CREATE INDEX IF NOT EXISTS ix_deleted_messages_source_app ON deleted_messages (source_app);

    -- Error logs
    CREATE INDEX IF NOT EXISTS ix_error_logs_case_id ON error_logs (case_id);
    CREATE INDEX IF NOT EXISTS ix_error_logs_timestamp ON error_logs (timestamp DESC);

    RAISE NOTICE 'Performance indexes created successfully';
END;
$$ LANGUAGE plpgsql;

-- Run the index creation
SELECT create_performance_indexes();

-- Create a view for quick stats
CREATE OR REPLACE VIEW v_case_stats AS
SELECT
    c.id as case_id,
    c.name as case_name,
    c.status,
    COUNT(DISTINCT e.id) as evidence_count,
    COUNT(DISTINCT wam.id) + COUNT(DISTINCT tgm.id) as total_messages,
    COUNT(DISTINCT wac.id) + COUNT(DISTINCT tgc.id) as total_contacts,
    COUNT(DISTINCT tm.id) as timeline_events,
    COUNT(DISTINCT dm.id) as deleted_detection_count,
    MAX(c.created_at) as last_updated
FROM cases c
LEFT JOIN evidence e ON e.case_id = c.id
LEFT JOIN wa_messages wam ON wam.evidence_id = e.id
LEFT JOIN tg_messages tgm ON tgm.evidence_id = e.id
LEFT JOIN wa_contacts wac ON wac.evidence_id = e.id
LEFT JOIN tg_contacts tgc ON tgc.evidence_id = e.id
LEFT JOIN timeline_events tm ON tm.case_id = c.id
LEFT JOIN deleted_messages dm ON dm.case_id = c.id
GROUP BY c.id, c.name, c.status;

COMMENT ON VIEW v_case_stats IS 'Aggregated statistics for all cases';

-- Grant permissions to public (if needed)
GRANT SELECT ON v_case_stats TO PUBLIC;