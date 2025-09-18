-- Add challenge_gate_accepted column to users table
-- This tracks whether a user has accepted the Riddle Master challenge

ALTER TABLE users ADD COLUMN challenge_gate_accepted BOOLEAN DEFAULT FALSE;

-- Update existing users to have the default value
UPDATE users SET challenge_gate_accepted = FALSE WHERE challenge_gate_accepted IS NULL;