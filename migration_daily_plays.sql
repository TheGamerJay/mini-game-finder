-- Migration for daily plays quota system
CREATE TABLE IF NOT EXISTS daily_plays (
  user_id   INTEGER NOT NULL,
  game_key  TEXT    NOT NULL,
  day_utc   DATE    NOT NULL,
  used      INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, game_key, day_utc)
);

-- Add missing columns defensively for existing tables
ALTER TABLE credit_txns ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(64);
ALTER TABLE scores ADD COLUMN IF NOT EXISTS duration_sec INTEGER;