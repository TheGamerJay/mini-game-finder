-- SQL commands to add progressive cooldown columns to production database
-- Run these in your PostgreSQL production database

-- Add recent_actions_hour column
ALTER TABLE user_community_stats
ADD COLUMN IF NOT EXISTS recent_actions_hour INTEGER DEFAULT 0 NOT NULL;

-- Add recent_actions_reset_at column
ALTER TABLE user_community_stats
ADD COLUMN IF NOT EXISTS recent_actions_reset_at TIMESTAMP;

-- Verify the columns were added
\d user_community_stats;

-- Optional: Check if any existing users need initialization
SELECT COUNT(*) FROM user_community_stats WHERE recent_actions_hour IS NULL;