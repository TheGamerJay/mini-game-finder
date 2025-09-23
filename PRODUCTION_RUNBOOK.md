# 🚀 PRODUCTION DATABASE SCHEMA FIX RUNBOOK

## Overview
This runbook addresses the systematic database schema mismatches causing 500 errors across community features. Based on comprehensive root cause analysis, the production PostgreSQL database has an outdated schema compared to what the application code expects.

## 🎯 Issues Being Fixed
- ❌ Community post deletion 500 errors (permanent reactions trigger conflict)
- ❌ Community reactions 500 errors (missing PRIMARY KEY constraints)
- ❌ Missing columns causing query failures (`credit_txns.idempotency_key`, `scores.duration_sec`, etc.)

---

## 📋 STEP-BY-STEP EXECUTION

### A. Prep & Safety

#### 1. Enable Degraded Mode (Blocks writes but keeps site up)
```bash
# In Railway → Settings → Variables
DEGRADED_MODE=1
```

#### 2. Take Database Backup
```bash
# Railway: Database → Backups/Snapshots
# OR manual backup:
pg_dump -Fc $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).dump
```

### B. Inspect Current Schema (Optional but Recommended)

Connect to production database:
```bash
# Railway → Database → Connect (get psql connection string)
psql $DATABASE_URL
```

Run diagnostic queries:
```sql
\d posts
\d post_reactions
\d credit_txns
\d scores

-- Check for missing PRIMARY KEY
SELECT
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE tablename = 'post_reactions' AND indexname LIKE '%pkey%';

-- Check foreign key constraints
SELECT conname, confdeltype FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
WHERE t.relname = 'post_reactions' AND c.contype = 'f';
```

### C. Apply Schema Repair (One-Shot, Idempotent)

#### 1. Open SQL Console to Production
```bash
# Use Railway "Connect" → copy psql connection string
psql $DATABASE_URL
```

#### 2. Execute Complete Schema Fix
```sql
-- Copy/paste the entire PRODUCTION_SCHEMA_FIX.sql file
-- It's idempotent - safe to run multiple times
\i PRODUCTION_SCHEMA_FIX.sql

-- OR copy/paste the SQL content directly
```

### D. Verify Migration Success

Run verification queries:
```sql
-- Check post_reactions PRIMARY KEY exists
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename = 'post_reactions' AND indexname LIKE '%pkey%';

-- Check foreign key constraint changed to SET NULL
SELECT
  conname,
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

-- Check new columns exist
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name IN ('credit_txns', 'scores', 'posts', 'users')
  AND column_name IN ('idempotency_key', 'duration_sec', 'is_hidden', 'is_deleted',
                      'moderation_status', 'challenge_penalty_until', 'boost_penalty_until')
ORDER BY table_name, column_name;

-- Check for orphaned reactions (should be minimal)
SELECT COUNT(*) as orphaned_reactions FROM post_reactions WHERE post_id IS NULL;
```

### E. Re-Enable Application

#### 1. Turn Off Degraded Mode
```bash
# Railway → Settings → Variables
# Remove or set to false: DEGRADED_MODE=false
```

#### 2. Verify Health
```bash
curl https://words.soulbridgeai.com/health
# Should return 200 OK
```

#### 3. Run Smoke Tests
```bash
# Local smoke tests
make smoke

# OR manually test:
curl https://words.soulbridgeai.com/api/word-finder/_ping
```

#### 4. Test Fixed Functionality
- ✅ Community post deletion (should work without 500 errors)
- ✅ Community reactions (should work without 500 errors)
- ✅ Credit transactions (should handle idempotency)
- ✅ Game scores (should record duration)

### F. Rollback (Only if needed)

If issues occur:
```bash
# Restore from backup taken in step A2
pg_restore -d $DATABASE_URL backup_YYYYMMDD_HHMMSS.dump

# Re-enable degraded mode if needed
DEGRADED_MODE=1
```

---

## 🔧 Technical Details

### What This Fix Does

#### 1. **Post Reactions PRIMARY KEY**
- Adds missing PRIMARY KEY constraint on `post_reactions(id)`
- Ensures proper indexing and referential integrity

#### 2. **Permanent Reactions Compatibility**
- Changes foreign key from `ON DELETE CASCADE` to `ON DELETE SET NULL`
- Allows post deletion while preserving reactions (respects permanent policy)
- Makes `post_id` nullable to support orphaned reactions

#### 3. **Missing Columns**
- Adds `credit_txns.idempotency_key` for transaction deduplication
- Adds `scores.duration_sec` for game timing data
- Adds posts columns: `is_hidden`, `is_deleted`, `moderation_status`
- Adds user penalty columns: `challenge_penalty_until`, `boost_penalty_until`

#### 4. **Performance Optimizations**
- Creates partial index on `post_reactions(post_id)` where not null
- Updates table statistics for better query planning

### Safety Features

- ✅ **Idempotent**: Safe to run multiple times, checks existence before changes
- ✅ **Non-destructive**: Adds columns/constraints, doesn't drop data
- ✅ **Graceful**: Handles existing data and maintains referential integrity
- ✅ **Rollback-friendly**: Changes can be reversed if needed

---

## 🚨 Troubleshooting

### Common Issues

#### If `post_reactions` table has no `id` column:
```sql
-- Stop migration and add surrogate key first:
ALTER TABLE post_reactions ADD COLUMN id SERIAL PRIMARY KEY;
-- Then re-run migration
```

#### If foreign key can't be dropped:
```sql
-- Check existing constraints:
\d post_reactions
-- Drop by correct name:
ALTER TABLE post_reactions DROP CONSTRAINT actual_constraint_name;
```

#### If trigger conflicts persist:
```sql
-- Check trigger function:
\df reactions_are_permanent
-- Ensure it only blocks DELETE, not UPDATE (for SET NULL to work)
```

### Verification Commands

```bash
# Test post deletion
curl -X DELETE https://words.soulbridgeai.com/community/delete/POST_ID \
  -H "X-CSRF-Token: TOKEN" \
  -H "Cookie: session=SESSION"

# Test reactions
curl -X POST https://words.soulbridgeai.com/community/react/POST_ID \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: TOKEN" \
  -H "Cookie: session=SESSION" \
  -d '{"reaction_type": "love"}'
```

---

## ✅ Success Criteria

After migration completion:

- ✅ No 500 errors on community post deletion
- ✅ No 500 errors on community reactions
- ✅ All smoke tests pass
- ✅ Community features work smoothly
- ✅ No data loss or corruption
- ✅ Performance maintained or improved

---

## 📞 Support

If issues arise during migration:
1. Check Railway application logs for specific errors
2. Verify database connection and constraints
3. Run diagnostic queries to confirm schema state
4. Rollback to backup if critical issues occur

**Emergency Contact**: Check application logs first, then restore from backup if needed.