-- Add proper JSONB column and indexes for game preferences
-- This migration is idempotent and can be run multiple times safely

-- 1) Ensure user_preferences is proper JSONB with default
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS user_preferences jsonb NOT NULL DEFAULT '{}'::jsonb;

-- 2) Add helper column for efficient TTL queries
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS prefs_updated_at timestamptz;

-- 3) Core indexes
CREATE INDEX IF NOT EXISTS idx_users_prefs_user ON users (id);
CREATE INDEX IF NOT EXISTS idx_users_prefs_updated_at ON users (prefs_updated_at DESC);

-- 4) Optional: GIN index for complex JSONB queries (if needed later)
-- CREATE INDEX IF NOT EXISTS idx_users_preferences_gin ON users USING gin (user_preferences);

-- 5) Update existing text columns to JSONB (if they exist)
-- This handles the migration from TEXT to JSONB safely
DO $$
BEGIN
  -- Check if user_preferences exists as text and convert
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users'
    AND column_name = 'user_preferences'
    AND data_type = 'text'
  ) THEN
    -- Convert existing text JSON to proper JSONB
    UPDATE users
    SET user_preferences = COALESCE(user_preferences::jsonb, '{}'::jsonb)
    WHERE user_preferences IS NOT NULL;

    -- Alter column type
    ALTER TABLE users ALTER COLUMN user_preferences TYPE jsonb USING user_preferences::jsonb;
  END IF;
END $$;