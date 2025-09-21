-- Fix post_reactions table structure - handle existing primary key
-- This addresses the "multiple primary key not allowed" error

BEGIN;

-- First, let's see the current table structure
-- Check if id column exists
DO $$
DECLARE
    has_id_column boolean := false;
    has_primary_key boolean := false;
    current_primary_key text;
BEGIN
    -- Check if id column exists
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'post_reactions' AND column_name = 'id'
    ) INTO has_id_column;

    -- Check current primary key
    SELECT constraint_name INTO current_primary_key
    FROM information_schema.table_constraints
    WHERE table_name = 'post_reactions'
    AND constraint_type = 'PRIMARY KEY'
    LIMIT 1;

    has_primary_key := (current_primary_key IS NOT NULL);

    RAISE NOTICE 'Table status - has_id_column: %, has_primary_key: %, current_pk: %',
                 has_id_column, has_primary_key, COALESCE(current_primary_key, 'none');

    IF NOT has_id_column THEN
        IF has_primary_key THEN
            -- Drop existing primary key constraint first
            RAISE NOTICE 'Dropping existing primary key constraint: %', current_primary_key;
            EXECUTE 'ALTER TABLE post_reactions DROP CONSTRAINT ' || current_primary_key;
        END IF;

        -- Add id column as primary key
        ALTER TABLE post_reactions ADD COLUMN id SERIAL PRIMARY KEY;
        RAISE NOTICE 'Added id column as new primary key';

    ELSE
        RAISE NOTICE 'id column already exists, no changes needed';
    END IF;
END $$;

COMMIT;

-- Show final table structure
\d post_reactions;