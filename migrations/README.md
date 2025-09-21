# Database Migrations

This directory contains Alembic database migrations for the clean architecture refactor.

## Setup

Alembic is configured to work with the existing models.py file and the new app.common.db infrastructure.

## Usage

### Create a new migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Create empty migration for manual changes
alembic revision -m "Manual migration description"
```

### Apply migrations

```bash
# Upgrade to latest migration
alembic upgrade head

# Upgrade to specific revision
alembic upgrade <revision_id>

# Downgrade to previous revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade <revision_id>
```

### Check migration status

```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic heads
```

## Migration Guidelines

1. **Always review auto-generated migrations** before applying them
2. **Test migrations on a copy of production data** before applying to production
3. **Prefer additive changes** that don't break existing code
4. **Use transactions** for complex migrations
5. **Include rollback logic** in downgrade() functions
6. **Document breaking changes** in migration comments

## Feature Ownership

Each feature owns its tables exclusively:

- `auth`: users, password_resets
- `posts`: posts
- `reactions`: post_reactions
- `comments`: comments (when implemented)
- `payments`: credit_txns_new, purchases, etc.

Cross-feature schema changes should be coordinated and documented.

## Production Deployment

1. Backup database before migration
2. Run migration in maintenance window if needed
3. Verify migration completed successfully
4. Monitor application after deployment
5. Have rollback plan ready