-- Promotion War System Database Migration
-- Creates new tables for strategic promotion wars with winner/loser consequences

BEGIN;

-- Create user_debuffs table for penalty tracking
CREATE TABLE IF NOT EXISTS user_debuffs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- PROMOTION_COOLDOWN, REDUCED_EFFECTIVENESS, HIGHER_COSTS, LOWER_PRIORITY
    severity FLOAT NOT NULL DEFAULT 1.0, -- Multiplier for effect strength
    expires_at TIMESTAMP NOT NULL,
    war_id INTEGER REFERENCES promotion_wars(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create user_discounts table for winner benefits
CREATE TABLE IF NOT EXISTS user_discounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- PROMOTION_DISCOUNT, EXTENDED_PROMOTION, PENALTY_IMMUNITY, PRIORITY_BOOST
    value FLOAT NOT NULL DEFAULT 1.0, -- Discount amount or boost multiplier
    uses_remaining INTEGER, -- For limited-use benefits like "next 3 promotions"
    expires_at TIMESTAMP NOT NULL,
    war_id INTEGER REFERENCES promotion_wars(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create promotion_wars table
CREATE TABLE IF NOT EXISTS promotion_wars (
    id SERIAL PRIMARY KEY,
    challenger_user_id INTEGER NOT NULL REFERENCES users(id),
    challenged_user_id INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, accepted, active, completed, expired
    starts_at TIMESTAMP,
    ends_at TIMESTAMP,
    challenger_score INTEGER DEFAULT 0 NOT NULL,
    challenged_score INTEGER DEFAULT 0 NOT NULL,
    winner_user_id INTEGER REFERENCES users(id),
    loser_user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create war_events table for tracking actions during wars
CREATE TABLE IF NOT EXISTS war_events (
    id SERIAL PRIMARY KEY,
    war_id INTEGER NOT NULL REFERENCES promotion_wars(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    post_id INTEGER NOT NULL REFERENCES posts(id),
    action VARCHAR(20) NOT NULL, -- promote, decline, accept
    points_earned INTEGER DEFAULT 0 NOT NULL,
    credits_spent INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_debuffs_user_id ON user_debuffs(user_id);
CREATE INDEX IF NOT EXISTS idx_user_debuffs_expires_at ON user_debuffs(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_debuffs_type ON user_debuffs(type);

CREATE INDEX IF NOT EXISTS idx_user_discounts_user_id ON user_discounts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_discounts_expires_at ON user_discounts(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_discounts_type ON user_discounts(type);

CREATE INDEX IF NOT EXISTS idx_promotion_wars_challenger ON promotion_wars(challenger_user_id);
CREATE INDEX IF NOT EXISTS idx_promotion_wars_challenged ON promotion_wars(challenged_user_id);
CREATE INDEX IF NOT EXISTS idx_promotion_wars_status ON promotion_wars(status);
CREATE INDEX IF NOT EXISTS idx_promotion_wars_ends_at ON promotion_wars(ends_at);

CREATE INDEX IF NOT EXISTS idx_war_events_war_id ON war_events(war_id);
CREATE INDEX IF NOT EXISTS idx_war_events_user_id ON war_events(user_id);

-- Add foreign key constraint for war_id in user_debuffs and user_discounts
-- (Note: These were referenced before the table was created, so we need to add them after)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'user_debuffs_war_id_fkey'
        AND table_name = 'user_debuffs'
    ) THEN
        ALTER TABLE user_debuffs ADD CONSTRAINT user_debuffs_war_id_fkey
        FOREIGN KEY (war_id) REFERENCES promotion_wars(id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'user_discounts_war_id_fkey'
        AND table_name = 'user_discounts'
    ) THEN
        ALTER TABLE user_discounts ADD CONSTRAINT user_discounts_war_id_fkey
        FOREIGN KEY (war_id) REFERENCES promotion_wars(id);
    END IF;
END $$;

COMMIT;

-- Verify the new tables were created
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('user_debuffs', 'user_discounts', 'promotion_wars', 'war_events')
ORDER BY table_name, ordinal_position;

RAISE NOTICE 'Promotion War System migration completed successfully!';