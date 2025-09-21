-- Fix posts table missing boost_cooldown_until column
-- This column is used for the Boost War penalty system to prevent posts from being boosted

BEGIN;

-- Add boost_cooldown_until column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'posts' AND column_name = 'boost_cooldown_until') THEN
        ALTER TABLE posts ADD COLUMN boost_cooldown_until TIMESTAMP NULL;
        RAISE NOTICE 'Added boost_cooldown_until column to posts table';
    ELSE
        RAISE NOTICE 'boost_cooldown_until column already exists in posts table';
    END IF;
END $$;

-- Add comment for documentation
COMMENT ON COLUMN posts.boost_cooldown_until IS 'Timestamp until when this post cannot be boosted (penalty system)';

COMMIT;

-- Verify the column was added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'posts'
AND column_name = 'boost_cooldown_until';