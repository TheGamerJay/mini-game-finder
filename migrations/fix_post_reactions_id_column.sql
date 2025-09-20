-- Fix missing id column in post_reactions table and ensure proper constraints
-- This migration adds the missing primary key column and ensures proper constraints

-- First, check if the table exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'post_reactions'
    ) THEN
        RAISE NOTICE 'post_reactions table does not exist, will be created by SQLAlchemy';
        RETURN;
    END IF;
END $$;

-- Add id column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'post_reactions'
        AND column_name = 'id'
    ) THEN
        -- Add the id column as BIGSERIAL
        ALTER TABLE post_reactions ADD COLUMN id BIGSERIAL;
        RAISE NOTICE 'Added id column to post_reactions table';
    ELSE
        RAISE NOTICE 'id column already exists in post_reactions table';
    END IF;
END $$;

-- Update primary key constraints
DO $$
BEGIN
    -- Drop existing primary key if it exists
    IF EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_name = 'post_reactions'
        AND constraint_type = 'PRIMARY KEY'
    ) THEN
        ALTER TABLE post_reactions DROP CONSTRAINT post_reactions_pkey;
        RAISE NOTICE 'Dropped existing primary key constraint';
    END IF;

    -- Add new primary key on id column
    ALTER TABLE post_reactions ADD CONSTRAINT post_reactions_pkey PRIMARY KEY (id);
    RAISE NOTICE 'Added primary key constraint on id column';
END $$;

-- Ensure unique constraint on (post_id, user_id)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'uq_post_user'
        AND table_name = 'post_reactions'
    ) THEN
        ALTER TABLE post_reactions
        ADD CONSTRAINT uq_post_user
        UNIQUE (post_id, user_id);
        RAISE NOTICE 'Added unique constraint uq_post_user to post_reactions table';
    ELSE
        RAISE NOTICE 'Unique constraint uq_post_user already exists';
    END IF;
END $$;

-- Ensure reaction_type column has proper default and NOT NULL constraint
DO $$
BEGIN
    -- Add default value for reaction_type if not set
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'post_reactions'
        AND column_name = 'reaction_type'
        AND column_default IS NULL
    ) THEN
        ALTER TABLE post_reactions ALTER COLUMN reaction_type SET DEFAULT 'love';
        RAISE NOTICE 'Set default value for reaction_type column';
    END IF;

    -- Make reaction_type NOT NULL
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'post_reactions'
        AND column_name = 'reaction_type'
        AND is_nullable = 'YES'
    ) THEN
        -- First update any NULL values
        UPDATE post_reactions SET reaction_type = 'love' WHERE reaction_type IS NULL;
        -- Then add NOT NULL constraint
        ALTER TABLE post_reactions ALTER COLUMN reaction_type SET NOT NULL;
        RAISE NOTICE 'Set reaction_type column to NOT NULL';
    END IF;
END $$;

-- Ensure created_at column exists with proper default
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'post_reactions'
        AND column_name = 'created_at'
    ) THEN
        ALTER TABLE post_reactions ADD COLUMN created_at TIMESTAMP DEFAULT NOW();
        RAISE NOTICE 'Added created_at column to post_reactions table';
    ELSE
        RAISE NOTICE 'created_at column already exists in post_reactions table';
    END IF;
END $$;