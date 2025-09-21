-- Fix community_mutes table if it doesn't exist
-- This table is used for user muting functionality in the community

BEGIN;

-- Create community_mutes table if it doesn't exist
CREATE TABLE IF NOT EXISTS community_mutes (
    id SERIAL PRIMARY KEY,
    muter_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    muted_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(muter_user_id, muted_user_id)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_community_mutes_muter ON community_mutes(muter_user_id);
CREATE INDEX IF NOT EXISTS idx_community_mutes_muted ON community_mutes(muted_user_id);

-- Add comment for documentation
COMMENT ON TABLE community_mutes IS 'Stores user muting relationships for community features';

COMMIT;

-- Verify the table exists
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name = 'community_mutes'
ORDER BY ordinal_position;