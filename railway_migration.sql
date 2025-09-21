-- Railway Migration Script - Create all missing tables for promotion war system
-- Run this on Railway Postgres database

-- Create user_debuffs table
CREATE TABLE IF NOT EXISTS user_debuffs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    debuff_type VARCHAR(50) NOT NULL,
    severity INTEGER NOT NULL DEFAULT 1,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create user_discounts table
CREATE TABLE IF NOT EXISTS user_discounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    discount_type VARCHAR(50) NOT NULL,
    discount_rate DECIMAL(5,2) NOT NULL DEFAULT 0.20,
    uses_remaining INTEGER NOT NULL DEFAULT 3,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create promotion_wars table
CREATE TABLE IF NOT EXISTS promotion_wars (
    id SERIAL PRIMARY KEY,
    challenger_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    challenged_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    challenger_post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    challenged_post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    winner_user_id INTEGER REFERENCES users(id),
    loser_user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    finalized_at TIMESTAMP NULL
);

-- Create war_events table
CREATE TABLE IF NOT EXISTS war_events (
    id SERIAL PRIMARY KEY,
    war_id INTEGER NOT NULL REFERENCES promotion_wars(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_debuffs_user_id ON user_debuffs(user_id);
CREATE INDEX IF NOT EXISTS idx_user_debuffs_expires_at ON user_debuffs(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_discounts_user_id ON user_discounts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_discounts_expires_at ON user_discounts(expires_at);
CREATE INDEX IF NOT EXISTS idx_promotion_wars_challenger ON promotion_wars(challenger_user_id);
CREATE INDEX IF NOT EXISTS idx_promotion_wars_challenged ON promotion_wars(challenged_user_id);
CREATE INDEX IF NOT EXISTS idx_promotion_wars_status ON promotion_wars(status);
CREATE INDEX IF NOT EXISTS idx_promotion_wars_created_at ON promotion_wars(created_at);
CREATE INDEX IF NOT EXISTS idx_war_events_war_id ON war_events(war_id);

-- Ensure notifications table exists (from earlier migration)
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    read_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);

-- Add unique constraint to prevent duplicate notifications
CREATE UNIQUE INDEX IF NOT EXISTS idx_notifications_unique ON notifications(user_id, type, message)
WHERE read_at IS NULL;