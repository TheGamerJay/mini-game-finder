-- 🧱 Block A — SQL (Postgres) migration for Credits System
-- Migration for implementing comprehensive credits and learning system

-- ========================================
-- 1) Users: track free games used (first 5 free)
-- ========================================
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS games_played_free INT NOT NULL DEFAULT 0;

-- ========================================
-- 2) Credits: balance per user (reuse existing mini_word_credits)
-- ========================================
-- Note: We already have mini_word_credits in users table, so we'll create
-- a view/function to map to the new API structure for compatibility

CREATE TABLE IF NOT EXISTS user_credits (
  user_id BIGINT PRIMARY KEY,
  balance INT NOT NULL DEFAULT 0,      -- credits (virtual, not money)
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed existing users with their current mini_word_credits balance
INSERT INTO user_credits(user_id, balance, updated_at)
SELECT id, COALESCE(mini_word_credits, 0), COALESCE(created_at, now())
FROM users
ON CONFLICT (user_id) DO UPDATE SET
  balance = COALESCE(EXCLUDED.balance, user_credits.balance),
  updated_at = now();

-- Create trigger to keep user_credits and users.mini_word_credits in sync
CREATE OR REPLACE FUNCTION sync_user_credits()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    -- Update users table when user_credits changes
    UPDATE users SET mini_word_credits = NEW.balance WHERE id = NEW.user_id;
    RETURN NEW;
  ELSIF TG_OP = 'INSERT' THEN
    -- Update users table when new user_credits record is created
    UPDATE users SET mini_word_credits = NEW.balance WHERE id = NEW.user_id;
    RETURN NEW;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_sync_user_credits ON user_credits;
CREATE TRIGGER trigger_sync_user_credits
  AFTER INSERT OR UPDATE ON user_credits
  FOR EACH ROW EXECUTE FUNCTION sync_user_credits();

-- ========================================
-- 3) Credit usage ledger (spends only)
-- ========================================
CREATE TABLE IF NOT EXISTS credit_usage (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  reason TEXT NOT NULL,                -- 'game_start' | 'reveal' | 'hint'
  amount INT NOT NULL CHECK (amount > 0),
  puzzle_id BIGINT,
  word_id BIGINT,
  before_balance INT NOT NULL,
  after_balance INT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_credit_usage_user ON credit_usage(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_usage_reason ON credit_usage(reason, created_at DESC);

-- ========================================
-- 4) Words master (for lessons) - enhance existing words table
-- ========================================
-- The words table already exists, let's enhance it for lessons
ALTER TABLE words
  ADD COLUMN IF NOT EXISTS definition TEXT,
  ADD COLUMN IF NOT EXISTS example TEXT,
  ADD COLUMN IF NOT EXISTS phonics TEXT,    -- e.g., "en-jin" or IPA format
  ADD COLUMN IF NOT EXISTS difficulty_level INT DEFAULT 1,
  ADD COLUMN IF NOT EXISTS category TEXT,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

-- Make text column case-insensitive if not already
-- Note: This will be handled by application logic if CITEXT extension isn't available

-- ========================================
-- 5) Puzzle-word mapping (coordinates & direction)
-- ========================================
-- Create new table for puzzle-word relationships with positioning
CREATE TABLE IF NOT EXISTS puzzle_words (
  id BIGSERIAL PRIMARY KEY,
  puzzle_id BIGINT NOT NULL,
  word_id BIGINT NOT NULL REFERENCES words(id),
  word_text TEXT NOT NULL,              -- denormalized for performance
  start_row INT NOT NULL,
  start_col INT NOT NULL,
  direction TEXT NOT NULL,              -- 'h','v','d1','d2' (horizontal, vertical, diagonal down-right, diagonal up-right)
  length INT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(puzzle_id, word_id)
);

CREATE INDEX IF NOT EXISTS idx_puzzle_words_puzzle ON puzzle_words(puzzle_id);
CREATE INDEX IF NOT EXISTS idx_puzzle_words_word ON puzzle_words(word_id);

-- ========================================
-- 6) User preferences (persist auto-teach/mute settings)
-- ========================================
CREATE TABLE IF NOT EXISTS user_prefs (
  user_id BIGINT NOT NULL REFERENCES users(id),
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, key)
);

CREATE INDEX IF NOT EXISTS idx_user_prefs_user ON user_prefs(user_id);

-- ========================================
-- 7) Game sessions (track game state and costs)
-- ========================================
CREATE TABLE IF NOT EXISTS game_sessions (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  puzzle_id BIGINT,
  mode TEXT NOT NULL,                   -- 'easy', 'medium', 'hard'
  category TEXT,
  cost_credits INT NOT NULL DEFAULT 0, -- 0 for free games, 5 for paid
  status TEXT NOT NULL DEFAULT 'active', -- 'active', 'completed', 'abandoned'
  words_found INT DEFAULT 0,
  total_words INT DEFAULT 0,
  score INT DEFAULT 0,
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_game_sessions_user ON game_sessions(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_game_sessions_status ON game_sessions(status, started_at DESC);

-- ========================================
-- 8) Word reveals (track revealed words with lessons)
-- ========================================
CREATE TABLE IF NOT EXISTS word_reveals (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  game_session_id BIGINT REFERENCES game_sessions(id),
  puzzle_id BIGINT,
  word_id BIGINT NOT NULL REFERENCES words(id),
  word_text TEXT NOT NULL,
  cost_credits INT NOT NULL DEFAULT 5,
  lesson_shown BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_word_reveals_user ON word_reveals(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_word_reveals_session ON word_reveals(game_session_id);

-- ========================================
-- 9) Seed some example words with definitions for testing
-- ========================================
INSERT INTO words (text, definition, example, phonics, difficulty_level, category) VALUES
  ('APPLE', 'A round fruit with red or green skin', 'I ate a red apple for lunch.', 'AP-ul', 1, 'food'),
  ('ROBOT', 'A machine that can perform tasks automatically', 'The robot helped clean the house.', 'ROH-bot', 2, 'technology'),
  ('TIGER', 'A large wild cat with orange fur and black stripes', 'The tiger prowled through the jungle.', 'TY-ger', 2, 'animals'),
  ('HOUSE', 'A building where people live', 'My house has a red door.', 'HOWS', 1, 'places'),
  ('OCEAN', 'A very large body of salt water', 'We swam in the ocean during our vacation.', 'OH-shun', 2, 'nature'),
  ('SMILE', 'To curve your mouth upward to show happiness', 'Her smile brightened the room.', 'SMYL', 1, 'emotions'),
  ('EAGLE', 'A large bird of prey with excellent eyesight', 'The eagle soared high above the mountains.', 'EE-gul', 2, 'animals'),
  ('MUSIC', 'Sounds arranged in a pleasing way', 'I love listening to music while I work.', 'MYOO-zik', 2, 'arts')
ON CONFLICT (text) DO UPDATE SET
  definition = EXCLUDED.definition,
  example = EXCLUDED.example,
  phonics = EXCLUDED.phonics,
  difficulty_level = EXCLUDED.difficulty_level,
  category = EXCLUDED.category;

-- ========================================
-- 10) Helper functions for the credits system
-- ========================================

-- Function to get user's current credit balance
CREATE OR REPLACE FUNCTION get_user_credits(p_user_id BIGINT)
RETURNS INT AS $$
DECLARE
  balance INT;
BEGIN
  SELECT COALESCE(user_credits.balance, users.mini_word_credits, 0)
  INTO balance
  FROM users
  LEFT JOIN user_credits ON users.id = user_credits.user_id
  WHERE users.id = p_user_id;

  RETURN COALESCE(balance, 0);
END;
$$ LANGUAGE plpgsql;

-- Function to spend credits atomically
CREATE OR REPLACE FUNCTION spend_user_credits(
  p_user_id BIGINT,
  p_amount INT,
  p_reason TEXT,
  p_puzzle_id BIGINT DEFAULT NULL,
  p_word_id BIGINT DEFAULT NULL
)
RETURNS INT AS $$
DECLARE
  current_balance INT;
  new_balance INT;
BEGIN
  -- Lock the user_credits row
  SELECT balance INTO current_balance
  FROM user_credits
  WHERE user_id = p_user_id
  FOR UPDATE;

  -- If no record exists, create one from users table
  IF current_balance IS NULL THEN
    INSERT INTO user_credits (user_id, balance)
    SELECT id, COALESCE(mini_word_credits, 0)
    FROM users
    WHERE id = p_user_id
    ON CONFLICT (user_id) DO NOTHING;

    SELECT balance INTO current_balance
    FROM user_credits
    WHERE user_id = p_user_id;
  END IF;

  -- Check if user has enough credits
  IF current_balance < p_amount THEN
    RAISE EXCEPTION 'INSUFFICIENT_CREDITS: User % has % credits, needs %',
      p_user_id, current_balance, p_amount;
  END IF;

  -- Calculate new balance
  new_balance := current_balance - p_amount;

  -- Update balance
  UPDATE user_credits
  SET balance = new_balance, updated_at = now()
  WHERE user_id = p_user_id;

  -- Log the usage
  INSERT INTO credit_usage (
    user_id, reason, amount, puzzle_id, word_id,
    before_balance, after_balance
  ) VALUES (
    p_user_id, p_reason, p_amount, p_puzzle_id, p_word_id,
    current_balance, new_balance
  );

  RETURN new_balance;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- 11) Migration completion log
-- ========================================
CREATE TABLE IF NOT EXISTS migration_log (
  id BIGSERIAL PRIMARY KEY,
  migration_name TEXT UNIQUE NOT NULL,
  applied_at TIMESTAMPTZ DEFAULT now(),
  description TEXT
);

INSERT INTO migration_log (migration_name, description) VALUES
  ('block_a_credits_system', 'Implemented comprehensive credits system with free games, word lessons, and user preferences')
ON CONFLICT (migration_name) DO UPDATE SET
  applied_at = now(),
  description = EXCLUDED.description;

-- ========================================
-- Migration completed successfully!
-- ========================================