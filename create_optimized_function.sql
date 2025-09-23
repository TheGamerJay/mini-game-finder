-- =============================================================================
-- CREATE OPTIMIZED COMMUNITY SUMMARY FUNCTION
-- Safe, index-friendly function that matches the app's expected signature
-- =============================================================================

-- Drop any old variants to avoid ambiguity
DROP FUNCTION IF EXISTS public.get_user_community_summary_optimized(integer);

-- Create the optimized summary function
CREATE OR REPLACE FUNCTION public.get_user_community_summary_optimized(p_user_id integer)
RETURNS TABLE(
  total_posts              bigint,
  reactions_received       bigint,
  posts_today              integer,
  remaining_today          integer,
  reactions_today          integer,
  reactions_remaining      integer
)
LANGUAGE sql
STABLE
AS $$
WITH caps AS (
  SELECT
    COALESCE(NULLIF(current_setting('app.posts_per_day',     true), '')::int, 10)  AS posts_cap,
    COALESCE(NULLIF(current_setting('app.reactions_per_day', true), '')::int, 50) AS reactions_cap
),
p AS (
  SELECT COUNT(*)::bigint AS total_posts
  FROM public.posts
  WHERE user_id = p_user_id
    AND is_deleted = false
),
rr AS (
  SELECT COUNT(*)::bigint AS reactions_received
  FROM public.post_reactions r
  JOIN public.posts        p2 ON p2.id = r.post_id
  WHERE p2.user_id = p_user_id
    AND p2.is_deleted = false
),
s AS (
  SELECT
    COALESCE(ucs.posts_today,     0) AS posts_today,
    COALESCE(ucs.reactions_today, 0) AS reactions_today
  FROM public.user_community_stats ucs
  WHERE ucs.user_id = p_user_id
)
SELECT
  (SELECT total_posts        FROM p)                                     AS total_posts,
  (SELECT reactions_received FROM rr)                                    AS reactions_received,
  (SELECT posts_today        FROM s)                                     AS posts_today,
  GREATEST( (SELECT posts_cap     FROM caps) - (SELECT posts_today FROM s), 0 ) AS remaining_today,
  (SELECT reactions_today    FROM s)                                     AS reactions_today,
  GREATEST( (SELECT reactions_cap FROM caps) - (SELECT reactions_today FROM s), 0 ) AS reactions_remaining;
$$;

-- Set database-level caps to match app configuration
-- (using 50 reactions per day to match current RATE_LIMITS in community_service.py)
SET app.posts_per_day = '10';
SET app.reactions_per_day = '50';

-- For production database persistence (uncomment after testing):
-- ALTER DATABASE your_db_name SET app.posts_per_day = '10';
-- ALTER DATABASE your_db_name SET app.reactions_per_day = '50';

-- =============================================================================
-- SMOKE TEST - Test with a real user
-- =============================================================================

-- Test the function with user ID 4 (replace with actual user ID from your system)
SELECT 'Smoke test for user ID 4:' AS test_description;
SELECT * FROM public.get_user_community_summary_optimized(4);

-- Expected result: One row with 6 columns
-- total_posts, reactions_received, posts_today, remaining_today, reactions_today, reactions_remaining

-- =============================================================================
-- PERFORMANCE INDEXES (if not already created)
-- =============================================================================

-- Index for posts by user (active posts)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_user_active_created
  ON public.posts (user_id, is_deleted, created_at DESC);

-- Index for reactions per post
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_reactions_post_created
  ON public.post_reactions (post_id, created_at DESC);

-- Index for join optimization (posts id, user, deleted status)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_id_user_deleted
  ON public.posts (id, user_id, is_deleted);

-- =============================================================================
-- DEPLOYMENT VERIFICATION
-- =============================================================================

-- 1. Verify function exists
SELECT proname, pronargs
FROM pg_proc
WHERE proname = 'get_user_community_summary_optimized';

-- 2. Test function returns expected columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'get_user_community_summary_optimized';

-- 3. Verify app settings
SELECT name, setting, source
FROM pg_settings
WHERE name LIKE 'app.%';

COMMENT ON FUNCTION public.get_user_community_summary_optimized(integer) IS
'Optimized community summary function - returns total_posts, reactions_received, posts_today, remaining_today, reactions_today, reactions_remaining for a user';

-- Function is ready! Next step: update community_service.py to use optimized path