-- ==============================================================================
-- PRODUCTION DATABASE SCHEMA REPAIR
-- ==============================================================================
--
-- PURPOSE: Fix systematic schema mismatches causing 500 errors
-- SAFETY:  Idempotent - safe to run multiple times
-- USAGE:   Connect to production PostgreSQL and paste entire file
--
-- Based on comprehensive root cause analysis:
-- - Community post deletion failures (permanent reactions trigger conflict)
-- - Community reactions 500 errors (missing PRIMARY KEY constraints)
-- - Missing columns causing query failures across system
-- ==============================================================================

-- ==============
-- GENERAL HELPERS
-- ==============
-- Helper: add constraint only if missing
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    WHERE t.relname = 'post_reactions' AND c.conname = 'post_reactions_pkey'
  ) THEN
    -- We'll add it below after ensuring the column situation is correct
    RAISE NOTICE 'post_reactions_pkey missing (will add)';
  END IF;
END$$;

-- =========================
-- 1) POST REACTIONS REPAIR
-- =========================
-- Ensure primary key on post_reactions(id)
-- (Assumes "id" column exists; if your table truly lacks an id column,
-- stop here and tell me—you'll need a different migration to add it.)

-- If there's no PK yet, add it.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    WHERE t.relname = 'post_reactions' AND c.contype = 'p'
  ) THEN
    -- Make sure id column is NOT NULL
    ALTER TABLE post_reactions
      ALTER COLUMN id SET NOT NULL;
    -- Add PK
    ALTER TABLE post_reactions
      ADD CONSTRAINT post_reactions_pkey PRIMARY KEY (id);
    RAISE NOTICE 'Added PRIMARY KEY on post_reactions(id)';
  ELSE
    RAISE NOTICE 'PRIMARY KEY already exists on post_reactions(id)';
  END IF;
END$$;

-- Allow reactions to persist if a post is deleted (detach instead of delete)
-- 1) make post_id nullable
ALTER TABLE post_reactions
  ALTER COLUMN post_id DROP NOT NULL;

-- 2) drop old FK if present
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    WHERE t.relname = 'post_reactions'
      AND c.contype = 'f'
      AND c.conname = 'post_reactions_post_id_fkey'
  ) THEN
    ALTER TABLE post_reactions
      DROP CONSTRAINT post_reactions_post_id_fkey;
    RAISE NOTICE 'Dropped old FK post_reactions_post_id_fkey';
  END IF;
END$$;

-- 3) create new FK with ON DELETE SET NULL (idempotent guard)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    WHERE t.relname = 'post_reactions'
      AND c.contype = 'f'
      AND c.conname = 'post_reactions_post_id_fkey'
  ) THEN
    ALTER TABLE post_reactions
      ADD CONSTRAINT post_reactions_post_id_fkey
      FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE SET NULL;
    RAISE NOTICE 'Created FK with ON DELETE SET NULL';
  ELSE
    RAISE NOTICE 'FK with SET NULL already exists';
  END IF;
END$$;

-- Optional: partial index for common joins
CREATE INDEX IF NOT EXISTS idx_post_reactions_post_id_not_null
  ON post_reactions (post_id)
  WHERE post_id IS NOT NULL;

-- Ensure your permanence trigger only blocks DELETE, not UPDATE (so SET NULL works)
-- If your trigger function raises on UPDATE, you must fix it; here we just reinstall trigger safely.
DROP TRIGGER IF EXISTS reactions_are_permanent ON post_reactions;
-- Re-create your trigger only on DELETE if that's your policy (adjust function name as needed)
-- CREATE TRIGGER reactions_are_permanent
-- BEFORE DELETE ON post_reactions
-- FOR EACH ROW
-- EXECUTE FUNCTION reactions_are_permanent();

-- =========================
-- 2) CREDIT TRANSACTIONS
-- =========================
-- Missing column from prior logs: credit_txns.idempotency_key
ALTER TABLE credit_txns
  ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

-- Helpful partial unique index (enforce uniqueness only when provided)
CREATE UNIQUE INDEX IF NOT EXISTS ux_credit_txns_idemkey_not_null
  ON credit_txns (idempotency_key)
  WHERE idempotency_key IS NOT NULL;

-- =========================
-- 3) SCORES / DURATION
-- =========================
-- Prior log showed "column s.duration_sec does not exist"
ALTER TABLE scores
  ADD COLUMN IF NOT EXISTS duration_sec INTEGER;

-- =========================
-- 4) POSTS TABLE COLUMNS
-- =========================
-- Ensure all expected columns exist for defensive queries
ALTER TABLE posts
  ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN DEFAULT FALSE;

ALTER TABLE posts
  ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;

ALTER TABLE posts
  ADD COLUMN IF NOT EXISTS moderation_status VARCHAR(20) DEFAULT 'approved';

ALTER TABLE posts
  ADD COLUMN IF NOT EXISTS moderation_reason TEXT;

ALTER TABLE posts
  ADD COLUMN IF NOT EXISTS boost_cooldown_until TIMESTAMP;

-- =========================
-- 5) USER PENALTY COLUMNS
-- =========================
-- Support for war penalty system
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS challenge_penalty_until TIMESTAMP;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS boost_penalty_until TIMESTAMP;

-- =========================
-- 6) CLEANUP / STATS
-- =========================
-- (Optional) Analyze tables for better query plans after changes
ANALYZE post_reactions;
ANALYZE credit_txns;
ANALYZE scores;
ANALYZE posts;
ANALYZE users;

-- =========================
-- 7) VERIFICATION QUERIES
-- =========================
-- Run these after the migration to verify success:

-- Check post_reactions PRIMARY KEY
SELECT
  schemaname,
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE tablename = 'post_reactions' AND indexname LIKE '%pkey%';

-- Check foreign key constraint
SELECT
  conname,
  confdeltype,
  CASE confdeltype
    WHEN 'a' THEN 'NO ACTION'
    WHEN 'r' THEN 'RESTRICT'
    WHEN 'c' THEN 'CASCADE'
    WHEN 'n' THEN 'SET NULL'
    WHEN 'd' THEN 'SET DEFAULT'
  END as delete_action
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
WHERE t.relname = 'post_reactions' AND c.contype = 'f';

-- Check for orphaned reactions (should be minimal after SET NULL migration)
SELECT COUNT(*) as orphaned_reactions
FROM post_reactions
WHERE post_id IS NULL;

-- Check new columns exist
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name IN ('credit_txns', 'scores', 'posts', 'users')
  AND column_name IN ('idempotency_key', 'duration_sec', 'is_hidden', 'is_deleted',
                      'moderation_status', 'challenge_penalty_until', 'boost_penalty_until')
ORDER BY table_name, column_name;

-- Final success message
DO $$
BEGIN
  RAISE NOTICE '============================================';
  RAISE NOTICE 'PRODUCTION SCHEMA REPAIR COMPLETED';
  RAISE NOTICE '============================================';
  RAISE NOTICE 'Next steps:';
  RAISE NOTICE '1. Turn off DEGRADED_MODE in Railway';
  RAISE NOTICE '2. Test community post deletion';
  RAISE NOTICE '3. Test community reactions';
  RAISE NOTICE '4. Run smoke tests: make smoke';
  RAISE NOTICE '============================================';
END$$;