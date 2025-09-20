# Database Fixes Migration

This directory contains migrations to fix critical database issues identified from production errors.

## Issues Fixed

### 1. Missing `id` column in `post_reactions` table
- **Error**: `column post_reactions.id does not exist`
- **Cause**: The `post_reactions` table was created without the primary key `id` column that the SQLAlchemy model expects
- **Fix**: `fix_post_reactions_id_column.sql` adds the missing `id SERIAL PRIMARY KEY` column

### 2. Null values in `users.email` column
- **Error**: `null value in column "email" of relation "users" violates not-null constraint`
- **Cause**: Existing users with null email addresses when the constraint expects non-null values
- **Fix**: `fix_users_email_nulls.sql` updates null emails with placeholder values and enforces the NOT NULL constraint

## Running the Migration

To apply these fixes to your production database:

```bash
# Set your database URL
export DATABASE_URL="your_production_database_url"

# Run the migration script
python run_database_fixes.py
```

## Migration Safety

- All migrations use `DO $$ ... END $$` blocks to check if changes are needed before applying them
- The migration script runs all changes in a single transaction that will rollback on any error
- Each migration checks for existing constraints/columns before attempting to modify them

## Files

- `fix_post_reactions_id_column.sql` - Adds missing id column to post_reactions table
- `fix_users_email_nulls.sql` - Fixes null email values in users table
- `../run_database_fixes.py` - Python script to execute all migrations safely