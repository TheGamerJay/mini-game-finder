-- Fix post_reactions table missing id primary key column
-- This is critical as the table needs a primary key for proper operation

BEGIN;

-- Check if id column exists, if not add it
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'post_reactions' AND column_name = 'id') THEN

        -- Add id column as primary key with auto-increment
        ALTER TABLE post_reactions ADD COLUMN id SERIAL PRIMARY KEY;

        RAISE NOTICE 'Added id column as primary key to post_reactions table';
    ELSE
        RAISE NOTICE 'id column already exists in post_reactions table';
    END IF;
EXCEPTION
    WHEN others THEN
        -- If there's an error (like table doesn't exist), create the whole table
        RAISE NOTICE 'Creating post_reactions table from scratch';

        CREATE TABLE IF NOT EXISTS post_reactions (
            id SERIAL PRIMARY KEY,
            post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            reaction_type VARCHAR(20) NOT NULL DEFAULT 'love',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            UNIQUE(post_id, user_id)
        );

        -- Add indexes for performance
        CREATE INDEX IF NOT EXISTS idx_post_reactions_post_id ON post_reactions(post_id);
        CREATE INDEX IF NOT EXISTS idx_post_reactions_user_id ON post_reactions(user_id);
END $$;

-- Add comment for documentation
COMMENT ON TABLE post_reactions IS 'User reactions to community posts (love, magic, peace, fire, etc.)';
COMMENT ON COLUMN post_reactions.id IS 'Primary key for post reactions';

COMMIT;

-- Verify the table structure
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'post_reactions'
ORDER BY ordinal_position;