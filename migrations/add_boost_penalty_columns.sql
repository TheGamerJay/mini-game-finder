-- Add boost_penalty_until and challenge_penalty_until columns to users table
-- These columns are used for the Boost War penalty system

-- Add boost_penalty_until column (nullable DateTime)
ALTER TABLE users ADD COLUMN IF NOT EXISTS boost_penalty_until TIMESTAMP NULL;

-- Add challenge_penalty_until column (nullable DateTime)
ALTER TABLE users ADD COLUMN IF NOT EXISTS challenge_penalty_until TIMESTAMP NULL;

-- Add comments for documentation
COMMENT ON COLUMN users.boost_penalty_until IS 'Timestamp until when user cannot boost posts (penalty system)';
COMMENT ON COLUMN users.challenge_penalty_until IS 'Timestamp until when user cannot create challenges (penalty system)';