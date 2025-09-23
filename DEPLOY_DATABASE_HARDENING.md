# Database Hardening Deployment Guide

## Overview
This guide implements comprehensive database hardening, performance optimization, and monitoring for the community system. Includes safety constraints, performance indexes, monitoring functions, and admin dashboard.

## Pre-Deployment Checklist

### 1. Backup Database
```bash
# Create backup before applying changes
pg_dump $DATABASE_URL > community_backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Check Data Integrity
```sql
-- Check for foreign key violations before adding constraints
SELECT COUNT(*) FROM user_community_stats s
LEFT JOIN users u ON u.id = s.user_id
WHERE u.id IS NULL;

-- Check for duplicate reactions before adding unique constraint
SELECT post_id, user_id, COUNT(*)
FROM post_reactions
GROUP BY post_id, user_id
HAVING COUNT(*) > 1;
```

## Step-by-Step Deployment

### Phase 1: Apply Database Hardening
```bash
# Execute the main hardening script
psql $DATABASE_URL -f database_hardening.sql
```

**What this does:**
- ✅ Adds primary key and foreign key constraints
- ✅ Creates performance indexes (CONCURRENTLY to avoid blocking)
- ✅ Installs optimized summary functions
- ✅ Sets up monitoring and health check functions
- ✅ Creates optional materialized views for heavy loads

### Phase 2: Verify Installation
```sql
-- Test the optimized summary function
SELECT * FROM public.get_user_community_summary_optimized(1);

-- Check system health
SELECT * FROM public.community_system_health();

-- Test monitoring functions
SELECT * FROM public.monitor_capped_users_by_timezone();
SELECT * FROM public.monitor_posts_distribution();
```

### Phase 3: Update Application
The application code has been updated to:
- ✅ Use optimized database functions with fallback
- ✅ Include admin monitoring dashboard
- ✅ Register admin routes and timezone management

## Production Monitoring Setup

### Cron Jobs
Add these to your production cron:

```bash
# Hourly: Reset daily limits at timezone boundaries
0 * * * * psql "$DATABASE_URL" -c "SELECT public.nightly_reset_local();" >> /var/log/community_reset.log 2>&1

# Daily: Refresh materialized views (if using them)
0 2 * * * psql "$DATABASE_URL" -c "SELECT public.refresh_user_activity_mv();" >> /var/log/community_mv.log 2>&1

# Weekly: Vacuum and analyze tables
0 3 * * 0 psql "$DATABASE_URL" -c "SELECT public.maintain_community_tables();" >> /var/log/community_vacuum.log 2>&1
```

### Health Monitoring
- **Admin Dashboard**: `/admin/community/health` (requires admin access)
- **API Endpoint**: `/api/admin/community/health` (JSON health data)
- **Smoke Tests**: Built-in user summary testing functions

## Performance Benefits

### Before Hardening
- Multiple separate queries for user summary
- No indexes on critical joins
- No data integrity constraints
- Manual calculation of statistics

### After Hardening
- Single optimized function call for user summary
- ⚡ Targeted indexes for fast dashboard loads
- 🔒 Foreign key constraints prevent data corruption
- 📊 Real-time monitoring and health checks
- 🧹 Automated maintenance functions

## Rollback Plan (If Needed)

### Remove Constraints
```sql
ALTER TABLE user_community_stats DROP CONSTRAINT user_community_stats_pkey;
ALTER TABLE user_community_stats DROP CONSTRAINT user_community_stats_user_fk;
ALTER TABLE posts DROP CONSTRAINT posts_user_fk;
ALTER TABLE post_reactions DROP CONSTRAINT post_reactions_unique;
```

### Remove Indexes
```sql
DROP INDEX CONCURRENTLY idx_posts_user_active_created;
DROP INDEX CONCURRENTLY idx_posts_user_created;
DROP INDEX CONCURRENTLY idx_post_reactions_post_created;
DROP INDEX CONCURRENTLY idx_post_reactions_user_created;
DROP INDEX CONCURRENTLY idx_posts_id_user_deleted;
DROP INDEX CONCURRENTLY idx_stats_posts_today;
```

### Remove Functions
```sql
DROP FUNCTION public.get_user_community_summary_optimized(BIGINT);
DROP FUNCTION public.monitor_capped_users_by_timezone();
DROP FUNCTION public.monitor_posts_distribution();
DROP FUNCTION public.community_system_health();
```

## Expected Improvements

### Performance
- **Dashboard Load Time**: 60-80% faster user summaries
- **Database Load**: Reduced query count from 3+ to 1 for user stats
- **Index Usage**: Optimized for common query patterns

### Reliability
- **Data Integrity**: Foreign key constraints prevent orphaned records
- **Unique Constraints**: Prevent duplicate reactions
- **Monitoring**: Real-time visibility into system health

### Operations
- **Admin Dashboard**: Complete health monitoring interface
- **Automated Maintenance**: Built-in vacuum and analyze functions
- **Health Checks**: Comprehensive system monitoring
- **Debugging Tools**: User-specific testing and diagnostics

## Monitoring Alerts (Recommended)

Set up alerts for:
- High percentage of capped users (>20% in any timezone)
- System health metrics outside normal ranges
- Failed daily reset operations
- Unusual posts distribution patterns

## Testing Checklist

After deployment, verify:
- [ ] Community page loads correctly
- [ ] User summary shows accurate data
- [ ] Admin dashboard accessible (admin users only)
- [ ] Daily limits working properly
- [ ] Timezone resets functioning
- [ ] Performance monitoring data updating

## Support & Troubleshooting

### Common Issues
1. **Constraint Violations**: Check data integrity before applying constraints
2. **Index Creation Timeouts**: Use CONCURRENTLY and monitor progress
3. **Function Errors**: Ensure all dependencies are installed
4. **Permission Issues**: Verify database user has sufficient privileges

### Debug Commands
```sql
-- Check index usage
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public';

-- Monitor constraint violations
SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint
WHERE contype = 'f';

-- Test user summary function
SELECT * FROM public.smoke_test_user_summary(YOUR_USER_ID);
```

This hardening significantly improves the community system's performance, reliability, and observability while maintaining full backward compatibility.