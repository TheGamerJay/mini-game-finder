-- Add riddle tables for Riddle Master Mini Game
-- This migration is idempotent and can be run multiple times safely

-- Create riddles table
CREATE TABLE IF NOT EXISTS riddles (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    hint TEXT,
    difficulty TEXT DEFAULT 'normal',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_riddles_difficulty ON riddles (difficulty);
CREATE INDEX IF NOT EXISTS idx_riddles_created_at ON riddles (created_at DESC);

-- Insert seed data (only if table is empty)
INSERT INTO riddles (question, answer, hint, difficulty)
SELECT * FROM (VALUES
    ('What has to be broken before you can use it?', 'egg|an egg|the egg', 'Breakfast thoughts…', 'easy'),
    ('I speak without a mouth and hear without ears. I have nobody, but I come alive with wind. What am I?', 'echo|an echo|the echo', 'You''ll hear me in canyons.', 'medium'),
    ('The more of this there is, the less you see. What is it?', 'darkness|the dark|dark', 'It shows up when the lights go out.', 'easy'),
    ('What month has 28 days?', 'all of them|all months|every month|all|all of em', 'Trick question 😉', 'easy'),
    ('I have branches, but no fruit, trunk or leaves. What am I?', 'bank|a bank|the bank', 'Not a tree.', 'medium'),
    ('What gets wetter the more it dries?', 'towel|a towel|the towel', 'It hangs in the bathroom.', 'easy'),
    ('What can you catch but not throw?', 'cold|a cold|the cold', 'You might need tissues.', 'easy'),
    ('I''m tall when I''m young, and I''m short when I''m old. What am I?', 'candle|a candle|the candle', 'It gives light.', 'easy'),
    ('What building has the most stories?', 'library|a library|the library', 'Full of books.', 'medium'),
    ('What goes up but never comes down?', 'age|your age', 'Everyone has one that increases.', 'easy'),
    ('What has keys but no locks, space but no room, you can enter but not go inside?', 'keyboard|a keyboard|the keyboard', 'You use it to type.', 'medium'),
    ('I''m not alive, but I grow; I don''t have lungs, but I need air; I don''t have a mouth, but water kills me. What am I?', 'fire|a fire|the fire', 'It needs oxygen to survive.', 'hard'),
    ('What comes once in a minute, twice in a moment, but never in a thousand years?', 'the letter m|letter m|m', 'Look at the letters in the words.', 'hard'),
    ('The person who makes it, sells it. The person who buys it, never uses it. The person who uses it, never knows it. What is it?', 'coffin|a coffin|the coffin', 'Something for the departed.', 'hard'),
    ('What runs around the whole yard without moving?', 'fence|a fence|the fence', 'It surrounds your property.', 'medium')
) AS seed_data
WHERE NOT EXISTS (SELECT 1 FROM riddles LIMIT 1);

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_riddles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS trigger_riddles_updated_at ON riddles;
CREATE TRIGGER trigger_riddles_updated_at
    BEFORE UPDATE ON riddles
    FOR EACH ROW
    EXECUTE FUNCTION update_riddles_updated_at();