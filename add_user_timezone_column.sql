-- Add timezone column to users table for timezone-aware daily limits
-- This column stores IANA timezone identifiers (e.g., 'America/New_York', 'Europe/London')

ALTER TABLE users
ADD COLUMN user_tz VARCHAR(50);

-- Add comment for documentation
COMMENT ON COLUMN users.user_tz IS 'IANA timezone identifier for user-specific daily limit resets';

-- Optional: Create index for faster timezone-based queries if needed
-- CREATE INDEX idx_users_timezone ON users(user_tz) WHERE user_tz IS NOT NULL;