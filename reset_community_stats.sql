-- =============================================================================
-- RESET COMMUNITY STATS FOR FRESH START
-- Resets all daily counters to zero and clears accumulated totals
-- =============================================================================

-- Reset all daily counters to zero
UPDATE public.user_community_stats
SET
    posts_today = 0,
    reactions_today = 0,
    reports_today = 0,
    -- Reset accumulated totals to zero for fresh start
    total_posts = 0,
    total_reactions_given = 0,
    total_reactions_received = 0,
    -- Update reset date to today
    last_reset_date = CURRENT_DATE,
    updated_at = NOW()
WHERE user_id IS NOT NULL;

-- Get count of affected rows
SELECT COUNT(*) as users_reset FROM public.user_community_stats;

-- Show sample of reset data
SELECT
    user_id,
    posts_today,
    reactions_today,
    total_posts,
    total_reactions_received,
    last_reset_date
FROM public.user_community_stats
ORDER BY user_id
LIMIT 10;

-- Update the database app settings to match new limits
SET app.posts_per_day = '10';
SET app.reactions_per_day = '25';

-- For permanent database-level settings (uncomment after testing):
-- ALTER DATABASE your_db_name SET app.posts_per_day = '10';
-- ALTER DATABASE your_db_name SET app.reactions_per_day = '25';

-- Verify new settings
SELECT name, setting, source
FROM pg_settings
WHERE name LIKE 'app.%'
ORDER BY name;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Check that all stats are reset
SELECT
    'posts_today' as metric,
    COUNT(*) as total_users,
    SUM(posts_today) as total_value,
    MAX(posts_today) as max_value
FROM public.user_community_stats
UNION ALL
SELECT
    'reactions_today' as metric,
    COUNT(*) as total_users,
    SUM(reactions_today) as total_value,
    MAX(reactions_today) as max_value
FROM public.user_community_stats
UNION ALL
SELECT
    'total_posts' as metric,
    COUNT(*) as total_users,
    SUM(total_posts) as total_value,
    MAX(total_posts) as max_value
FROM public.user_community_stats;

-- All total_value and max_value should be 0

-- Test the optimized function with reset data
SELECT 'User 4 after reset:' as description;
SELECT * FROM public.get_user_community_summary_optimized(4);

-- Expected: total_posts=0, reactions_received=0, posts_today=0, remaining_today=10, reactions_today=0, reactions_remaining=25

COMMENT ON TABLE public.user_community_stats IS 'Community stats reset for fresh start - all counters at zero';

-- =============================================================================
-- FRESH START CONFIRMATION
-- =============================================================================

\echo 'Community stats reset complete!'
\echo 'All daily counters: 0'
\echo 'All total counters: 0'
\echo 'New reaction limit: 25 per day'
\echo 'Display format: 0/25 style counters'
\echo 'Ready for fresh community activity!'