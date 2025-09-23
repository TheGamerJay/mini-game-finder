-- =============================================================================
-- DATABASE HARDENING & PERFORMANCE OPTIMIZATION
-- Community System Safety, Constraints, Indexes, and Monitoring
-- =============================================================================

-- =============================================================================
-- 1) SAFETY & CONSTRAINTS (one-time schema hardening)
-- =============================================================================

-- user_community_stats: primary key & FK constraints
ALTER TABLE public.user_community_stats
  ADD CONSTRAINT user_community_stats_pkey PRIMARY KEY (user_id);

ALTER TABLE public.user_community_stats
  ADD CONSTRAINT user_community_stats_user_fk
  FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

-- posts: typical integrity constraints
ALTER TABLE public.posts
  ADD CONSTRAINT posts_user_fk
  FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

-- post_reactions: ensure a user can react only once per post
ALTER TABLE public.post_reactions
  ADD CONSTRAINT post_reactions_unique UNIQUE (post_id, user_id);

-- =============================================================================
-- 2) PERFORMANCE INDEX KIT (fast reads for dashboard & caps)
-- =============================================================================

-- ⚡ Posts per user (ignore deleted), ordered by time
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_user_active_created
  ON public.posts (user_id, is_deleted, created_at DESC);

-- Posts per user regardless of deleted status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_user_created
  ON public.posts (user_id, created_at DESC)
  INCLUDE (is_deleted);

-- ⚡ Reactions per post (and time)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_reactions_post_created
  ON public.post_reactions (post_id, created_at DESC);

-- Reactions given by a user
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_post_reactions_user_created
  ON public.post_reactions (user_id, created_at DESC)
  INCLUDE (post_id);

-- ⚡ Join helper: look up user's posts by id quickly during reaction joins
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_id_user_deleted
  ON public.posts (id, user_id, is_deleted);

-- Query "who is capped?" efficiently
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stats_posts_today
  ON public.user_community_stats (posts_today);

-- Partial index on active posts only (more efficient for common queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_user_active_partial
  ON public.posts (user_id, created_at DESC)
  WHERE is_deleted = false;

-- Covering index to avoid heap lookups (PostgreSQL ≥11)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_user_created_inc
  ON public.posts (user_id, created_at DESC)
  INCLUDE (is_deleted);

-- =============================================================================
-- 3) OPTIMIZED COMMUNITY SUMMARY FUNCTION
-- =============================================================================

-- Single round-trip query for complete user community summary
CREATE OR REPLACE FUNCTION public.get_user_community_summary_optimized(user_id_param BIGINT)
RETURNS TABLE (
    total_posts INTEGER,
    reactions_received INTEGER,
    posts_today INTEGER,
    remaining_today INTEGER,
    reactions_today INTEGER,
    reactions_remaining INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH
    p AS (
        SELECT COUNT(*)::INTEGER AS total_posts
        FROM public.posts
        WHERE user_id = user_id_param AND is_deleted = false
    ),
    rr AS (
        SELECT COUNT(*)::INTEGER AS reactions_received
        FROM public.post_reactions r
        JOIN public.posts p ON p.id = r.post_id
        WHERE p.user_id = user_id_param AND p.is_deleted = false
    ),
    dl AS (
        SELECT
            posts_today,
            GREATEST(10 - posts_today, 0)::INTEGER AS remaining_today,
            reactions_today,
            GREATEST(50 - reactions_today, 0)::INTEGER AS reactions_remaining
        FROM public.user_community_stats
        WHERE user_id = user_id_param
    )
    SELECT p.total_posts, rr.reactions_received, dl.posts_today, dl.remaining_today, dl.reactions_today, dl.reactions_remaining
    FROM p, rr, dl;
END;
$$ LANGUAGE plpgsql STABLE;

-- =============================================================================
-- 4) MATERIALIZED VIEW FOR HEAVY DASHBOARDS (optional)
-- =============================================================================

-- Per-user activity counters (posts & reactions received)
CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_user_activity AS
SELECT
  u.id AS user_id,
  COALESCE((
    SELECT COUNT(*)
    FROM public.posts p
    WHERE p.user_id = u.id AND p.is_deleted = false
  ),0)::INTEGER AS total_posts,
  COALESCE((
    SELECT COUNT(*)
    FROM public.post_reactions r
    JOIN public.posts p ON p.id = r.post_id
    WHERE p.user_id = u.id AND p.is_deleted = false
  ),0)::INTEGER AS reactions_received,
  NOW() AS last_updated
FROM public.users u;

-- Index on the materialized view
CREATE INDEX IF NOT EXISTS idx_mv_user_activity_user
  ON public.mv_user_activity (user_id);

-- Function to refresh materialized view safely
CREATE OR REPLACE FUNCTION public.refresh_user_activity_mv()
RETURNS INTEGER AS $$
DECLARE
    rows_affected INTEGER;
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_user_activity;
    GET DIAGNOSTICS rows_affected = ROW_COUNT;
    RETURN rows_affected;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 5) MONITORING & HEALTH CHECK FUNCTIONS
-- =============================================================================

-- Track "who is capped" and distribution by timezone
CREATE OR REPLACE FUNCTION public.monitor_capped_users_by_timezone()
RETURNS TABLE (
    user_timezone TEXT,
    capped_users BIGINT,
    total_users BIGINT,
    cap_percentage NUMERIC(5,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(u.user_tz, 'UTC') AS user_timezone,
        COUNT(*) FILTER (WHERE s.posts_today >= 10) AS capped_users,
        COUNT(*) AS total_users,
        ROUND(
            (COUNT(*) FILTER (WHERE s.posts_today >= 10) * 100.0 / NULLIF(COUNT(*), 0)),
            2
        ) AS cap_percentage
    FROM public.user_community_stats s
    JOIN public.users u ON u.id = s.user_id
    GROUP BY u.user_tz
    ORDER BY capped_users DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- Distribution of posts_today across all users
CREATE OR REPLACE FUNCTION public.monitor_posts_distribution()
RETURNS TABLE (
    posts_today INTEGER,
    user_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT s.posts_today, COUNT(*) as user_count
    FROM public.user_community_stats s
    GROUP BY s.posts_today
    ORDER BY s.posts_today;
END;
$$ LANGUAGE plpgsql STABLE;

-- System health overview
CREATE OR REPLACE FUNCTION public.community_system_health()
RETURNS TABLE (
    metric TEXT,
    value BIGINT,
    description TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'total_active_users'::TEXT, COUNT(*)::BIGINT, 'Users with community stats'::TEXT
    FROM public.user_community_stats
    UNION ALL
    SELECT 'total_posts'::TEXT, COUNT(*)::BIGINT, 'All posts (including deleted)'::TEXT
    FROM public.posts
    UNION ALL
    SELECT 'active_posts'::TEXT, COUNT(*)::BIGINT, 'Non-deleted posts'::TEXT
    FROM public.posts WHERE is_deleted = false
    UNION ALL
    SELECT 'total_reactions'::TEXT, COUNT(*)::BIGINT, 'All reactions'::TEXT
    FROM public.post_reactions
    UNION ALL
    SELECT 'capped_users_today'::TEXT, COUNT(*)::BIGINT, 'Users at daily post limit'::TEXT
    FROM public.user_community_stats WHERE posts_today >= 10
    UNION ALL
    SELECT 'users_with_timezone'::TEXT, COUNT(*)::BIGINT, 'Users with custom timezone set'::TEXT
    FROM public.users WHERE user_tz IS NOT NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- =============================================================================
-- 6) SMOKE TEST FUNCTIONS
-- =============================================================================

-- Comprehensive user summary smoke test
CREATE OR REPLACE FUNCTION public.smoke_test_user_summary(test_user_id BIGINT)
RETURNS TABLE (
    test_name TEXT,
    result TEXT,
    expected_type TEXT,
    actual_value TEXT
) AS $$
DECLARE
    total_posts_count INTEGER;
    reactions_received_count INTEGER;
    posts_today_count INTEGER;
    remaining_today_count INTEGER;
BEGIN
    -- Get the optimized summary
    SELECT * FROM public.get_user_community_summary_optimized(test_user_id)
    INTO total_posts_count, reactions_received_count, posts_today_count, remaining_today_count;

    -- Test results
    RETURN QUERY
    SELECT 'total_posts'::TEXT,
           CASE WHEN total_posts_count >= 0 THEN 'PASS' ELSE 'FAIL' END::TEXT,
           'non_negative_integer'::TEXT,
           total_posts_count::TEXT
    UNION ALL
    SELECT 'reactions_received'::TEXT,
           CASE WHEN reactions_received_count >= 0 THEN 'PASS' ELSE 'FAIL' END::TEXT,
           'non_negative_integer'::TEXT,
           reactions_received_count::TEXT
    UNION ALL
    SELECT 'posts_today'::TEXT,
           CASE WHEN posts_today_count >= 0 AND posts_today_count <= 10 THEN 'PASS' ELSE 'FAIL' END::TEXT,
           'integer_0_to_10'::TEXT,
           posts_today_count::TEXT
    UNION ALL
    SELECT 'remaining_today'::TEXT,
           CASE WHEN remaining_today_count >= 0 AND remaining_today_count <= 10 THEN 'PASS' ELSE 'FAIL' END::TEXT,
           'integer_0_to_10'::TEXT,
           remaining_today_count::TEXT;
END;
$$ LANGUAGE plpgsql STABLE;

-- =============================================================================
-- 7) MAINTENANCE & ANALYTICS
-- =============================================================================

-- Update table statistics for optimal query planning
CREATE OR REPLACE FUNCTION public.update_community_stats()
RETURNS TEXT AS $$
BEGIN
    ANALYZE public.posts;
    ANALYZE public.post_reactions;
    ANALYZE public.user_community_stats;
    ANALYZE public.users;

    RETURN 'Statistics updated for all community tables';
END;
$$ LANGUAGE plpgsql;

-- Vacuum and analyze community tables
CREATE OR REPLACE FUNCTION public.maintain_community_tables()
RETURNS TEXT AS $$
BEGIN
    VACUUM (ANALYZE) public.posts;
    VACUUM (ANALYZE) public.post_reactions;
    VACUUM (ANALYZE) public.user_community_stats;

    RETURN 'Vacuum and analyze completed for community tables';
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- DEPLOYMENT NOTES
-- =============================================================================

/*
DEPLOYMENT CHECKLIST:

1. Run constraints first (may fail if data integrity issues exist):
   - Fix any foreign key violations before applying constraints
   - Check for duplicate post_reactions before adding unique constraint

2. Create indexes with CONCURRENTLY in production:
   - All CREATE INDEX statements use CONCURRENTLY to avoid blocking
   - Monitor index creation progress with:
     SELECT * FROM pg_stat_progress_create_index;

3. Test the optimized function:
   SELECT * FROM public.get_user_community_summary_optimized(YOUR_USER_ID);

4. Optional materialized view setup:
   REFRESH MATERIALIZED VIEW public.mv_user_activity;

5. Set up monitoring cron jobs:
   - Hourly: SELECT public.nightly_reset_local();
   - Daily: SELECT public.refresh_user_activity_mv();
   - Weekly: SELECT public.maintain_community_tables();

6. Health checks:
   SELECT * FROM public.community_system_health();
   SELECT * FROM public.monitor_capped_users_by_timezone();
   SELECT * FROM public.monitor_posts_distribution();

ROLLBACK PLAN:
- Drop indexes: DROP INDEX CONCURRENTLY index_name;
- Drop constraints: ALTER TABLE table_name DROP CONSTRAINT constraint_name;
- Drop functions: DROP FUNCTION function_name();
*/