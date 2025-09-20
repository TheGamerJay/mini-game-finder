-- Fix null email values in users table
-- This migration handles users with null email addresses

-- Update null email addresses with a default placeholder
UPDATE users
SET email = 'user_' || id || '@noemail.placeholder'
WHERE email IS NULL;

-- Ensure email column is not nullable (in case constraint is missing)
DO $$
BEGIN
    -- Check if email column allows nulls
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name = 'email'
        AND is_nullable = 'YES'
    ) THEN
        -- Make email column NOT NULL
        ALTER TABLE users ALTER COLUMN email SET NOT NULL;
        RAISE NOTICE 'Set email column to NOT NULL in users table';
    ELSE
        RAISE NOTICE 'Email column is already NOT NULL in users table';
    END IF;
END $$;

-- Ensure unique constraint exists on email
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = 'users'
        AND kcu.column_name = 'email'
        AND tc.constraint_type = 'UNIQUE'
    ) THEN
        -- Add unique constraint
        ALTER TABLE users ADD CONSTRAINT users_email_unique UNIQUE (email);
        RAISE NOTICE 'Added unique constraint on email column';
    ELSE
        RAISE NOTICE 'Unique constraint on email column already exists';
    END IF;
END $$;