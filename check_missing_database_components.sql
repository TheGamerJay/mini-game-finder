-- Comprehensive check for missing database tables and columns
-- Run this to identify what's missing in production

-- Check for missing tables
SELECT 'Missing Table: ' || table_name as issue
FROM (
    VALUES
    ('users'), ('scores'), ('credit_txns'), ('purchases'), ('puzzle_bank'),
    ('posts'), ('post_reactions'), ('post_reports'), ('user_community_stats'),
    ('community_mutes'), ('credit_txns_v2'), ('post_boosts'), ('boost_wars'),
    ('boost_war_actions'), ('user_badges'), ('scheduler_state')
) AS expected_tables(table_name)
WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_name = expected_tables.table_name
);

-- Check for missing columns in users table
SELECT 'Missing Column: users.' || column_name as issue
FROM (
    VALUES
    ('id'), ('email'), ('password_hash'), ('username'), ('display_name'),
    ('profile_image_url'), ('profile_image_data'), ('profile_image_mime_type'),
    ('profile_image_updated_at'), ('display_name_updated_at'), ('mini_word_credits'),
    ('games_played_free'), ('user_preferences'), ('welcome_pack_purchased'),
    ('war_wins'), ('boost_penalty_until'), ('challenge_penalty_until'),
    ('is_admin'), ('is_banned'), ('created_at')
) AS expected_columns(column_name)
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users')
AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = expected_columns.column_name
);

-- Check for missing columns in posts table
SELECT 'Missing Column: posts.' || column_name as issue
FROM (
    VALUES
    ('id'), ('user_id'), ('body'), ('image_url'), ('image_width'), ('image_height'),
    ('category'), ('content_type'), ('boost_score'), ('last_boost_at'),
    ('boost_cooldown_until'), ('is_hidden'), ('is_deleted'), ('moderation_status'),
    ('moderation_reason'), ('created_at'), ('updated_at')
) AS expected_columns(column_name)
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'posts')
AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'posts' AND column_name = expected_columns.column_name
);

-- Check for missing columns in credit_txns table
SELECT 'Missing Column: credit_txns.' || column_name as issue
FROM (
    VALUES
    ('id'), ('user_id'), ('amount_delta'), ('reason'), ('ref_txn_id'),
    ('idempotency_key'), ('created_at')
) AS expected_columns(column_name)
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'credit_txns')
AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'credit_txns' AND column_name = expected_columns.column_name
);

-- Check for missing columns in post_reactions table (with id column)
SELECT 'Missing Column: post_reactions.' || column_name as issue
FROM (
    VALUES
    ('id'), ('post_id'), ('user_id'), ('reaction_type'), ('created_at')
) AS expected_columns(column_name)
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'post_reactions')
AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'post_reactions' AND column_name = expected_columns.column_name
);

-- Show current state summary
SELECT
    'Current Tables Count: ' || COUNT(*) as summary
FROM information_schema.tables
WHERE table_schema = 'public';

SELECT
    'Current users Columns Count: ' || COUNT(*) as summary
FROM information_schema.columns
WHERE table_name = 'users';

SELECT
    'Current posts Columns Count: ' || COUNT(*) as summary
FROM information_schema.columns
WHERE table_name = 'posts';