-- Emergency fix for production database missing columns
-- Run this on the production database to fix the boost_penalty_until and challenge_penalty_until column errors

BEGIN;

-- Add boost_penalty_until column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'users' AND column_name = 'boost_penalty_until') THEN
        ALTER TABLE users ADD COLUMN boost_penalty_until TIMESTAMP NULL;
        RAISE NOTICE 'Added boost_penalty_until column';
    ELSE
        RAISE NOTICE 'boost_penalty_until column already exists';
    END IF;
END $$;

-- Add challenge_penalty_until column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'users' AND column_name = 'challenge_penalty_until') THEN
        ALTER TABLE users ADD COLUMN challenge_penalty_until TIMESTAMP NULL;
        RAISE NOTICE 'Added challenge_penalty_until column';
    ELSE
        RAISE NOTICE 'challenge_penalty_until column already exists';
    END IF;
END $$;

-- Add comments for documentation
COMMENT ON COLUMN users.boost_penalty_until IS 'Timestamp until when user cannot boost posts (penalty system)';
COMMENT ON COLUMN users.challenge_penalty_until IS 'Timestamp until when user cannot create challenges (penalty system)';

COMMIT;

-- Verify the columns were added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name IN ('boost_penalty_until', 'challenge_penalty_until')
ORDER BY column_name;