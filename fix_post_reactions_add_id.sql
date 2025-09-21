-- Fix post_reactions table - add id column while preserving existing structure
-- Handle the existing composite primary key properly

BEGIN;

-- Step 1: Check if id column already exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'post_reactions' AND column_name = 'id') THEN

        -- Step 2: Add id column (but not as primary key yet)
        ALTER TABLE post_reactions ADD COLUMN id SERIAL;
        RAISE NOTICE 'Added id column to post_reactions';

        -- Step 3: Drop the existing composite primary key
        ALTER TABLE post_reactions DROP CONSTRAINT post_reactions_pkey;
        RAISE NOTICE 'Dropped existing composite primary key';

        -- Step 4: Make id the new primary key
        ALTER TABLE post_reactions ADD PRIMARY KEY (id);
        RAISE NOTICE 'Set id as new primary key';

        -- Step 5: Add unique constraint to maintain data integrity
        ALTER TABLE post_reactions ADD CONSTRAINT post_reactions_unique_user_post
        UNIQUE (post_id, user_id);
        RAISE NOTICE 'Added unique constraint on (post_id, user_id)';

    ELSE
        RAISE NOTICE 'id column already exists in post_reactions table';
    END IF;
END $$;

COMMIT;

-- Verify final structure
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'post_reactions'
ORDER BY ordinal_position;

-- Show constraints
SELECT
    constraint_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'post_reactions';