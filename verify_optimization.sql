-- =============================================================================
-- VERIFICATION SCRIPT FOR OPTIMIZED COMMUNITY SUMMARY
-- Run this after deploying create_optimized_function.sql
-- =============================================================================

-- 1. Verify function exists and has correct signature
SELECT
    proname AS function_name,
    pronargs AS num_arguments,
    pg_get_function_identity_arguments(oid) AS arguments,
    pg_get_function_result(oid) AS return_type
FROM pg_proc
WHERE proname = 'get_user_community_summary_optimized';

-- Expected result: One row showing the function exists

-- 2. Test function with real user data
-- Replace 4 with an actual user ID from your system
\echo 'Testing optimized function with user ID 4:'
SELECT * FROM public.get_user_community_summary_optimized(4);

-- Expected result: One row with 6 columns
-- Example: total_posts | reactions_received | posts_today | remaining_today | reactions_today | reactions_remaining
--              15      |         23         |      3      |        7        |        5        |        45

-- 3. Compare with a few different users to verify data consistency
\echo 'Testing with multiple users:'
SELECT
    4 as user_id,
    total_posts,
    reactions_received,
    posts_today,
    remaining_today,
    reactions_today,
    reactions_remaining
FROM public.get_user_community_summary_optimized(4)
UNION ALL
SELECT
    1 as user_id,
    total_posts,
    reactions_received,
    posts_today,
    remaining_today,
    reactions_today,
    reactions_remaining
FROM public.get_user_community_summary_optimized(1)
ORDER BY user_id;

-- 4. Verify app settings are configured
\echo 'Checking app configuration settings:'
SELECT name, setting, source, sourcefile
FROM pg_settings
WHERE name LIKE 'app.%'
ORDER BY name;

-- Expected results:
-- app.posts_per_day     | 10 | session |
-- app.reactions_per_day | 50 | session |

-- 5. Check that required indexes exist for performance
\echo 'Checking performance indexes:'
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
    'idx_posts_user_active_created',
    'idx_post_reactions_post_created',
    'idx_posts_id_user_deleted'
  )
ORDER BY tablename, indexname;

-- 6. Performance test - should be fast even with larger datasets
\echo 'Performance test - timing the function:'
\timing on
SELECT COUNT(*) as test_runs
FROM (
    SELECT * FROM public.get_user_community_summary_optimized(4)
    UNION ALL
    SELECT * FROM public.get_user_community_summary_optimized(1)
    UNION ALL
    SELECT * FROM public.get_user_community_summary_optimized(2)
    UNION ALL
    SELECT * FROM public.get_user_community_summary_optimized(3)
) results;
\timing off

-- Should complete in under 50ms for 4 users

-- 7. Verify data integrity - compare totals with manual counts
\echo 'Data integrity check for user 4:'
WITH manual_count AS (
    SELECT
        COUNT(CASE WHEN NOT is_deleted THEN 1 END)::bigint as manual_total_posts,
        (
            SELECT COUNT(*)::bigint
            FROM post_reactions pr
            JOIN posts p ON p.id = pr.post_id
            WHERE p.user_id = 4 AND NOT p.is_deleted
        ) as manual_reactions_received,
        (
            SELECT COALESCE(posts_today, 0)
            FROM user_community_stats
            WHERE user_id = 4
        ) as manual_posts_today
    FROM posts
    WHERE user_id = 4
),
optimized AS (
    SELECT
        total_posts,
        reactions_received,
        posts_today
    FROM public.get_user_community_summary_optimized(4)
)
SELECT
    'total_posts' as metric,
    manual_count.manual_total_posts as manual_value,
    optimized.total_posts as optimized_value,
    (manual_count.manual_total_posts = optimized.total_posts) as values_match
FROM manual_count, optimized
UNION ALL
SELECT
    'reactions_received' as metric,
    manual_count.manual_reactions_received as manual_value,
    optimized.reactions_received as optimized_value,
    (manual_count.manual_reactions_received = optimized.reactions_received) as values_match
FROM manual_count, optimized
UNION ALL
SELECT
    'posts_today' as metric,
    manual_count.manual_posts_today as manual_value,
    optimized.posts_today as optimized_value,
    (manual_count.manual_posts_today = optimized.posts_today) as values_match
FROM manual_count, optimized;

-- All values_match should be true

-- =============================================================================
-- END-TO-END CHECKLIST
-- =============================================================================

\echo '=== DEPLOYMENT VERIFICATION CHECKLIST ==='
\echo '[ ] Function exists and returns data'
\echo '[ ] App settings configured (posts_per_day=10, reactions_per_day=50)'
\echo '[ ] Performance indexes created'
\echo '[ ] Function executes quickly (< 50ms for multiple users)'
\echo '[ ] Data integrity verified (manual counts match optimized function)'
\echo '[ ] Ready to test /community page with optimized path enabled'

\echo ''
\echo 'Next steps:'
\echo '1. Deploy updated community_service.py with optimized path enabled'
\echo '2. Test /community page - should load without UndefinedFunction errors'
\echo '3. Monitor logs for "Optimized function missing" warnings (should not appear)'
\echo '4. Verify user stats display correctly on community page'