# Database Migrations

This directory contains SQL migration scripts for the Mini Word Finder application.

## Block A - Credits System Migration

**File**: `block_a_credits_system.sql`
**Runner**: `run_block_a_migration.py`

### What it does:
1. **Free Games Tracking** - Adds `games_played_free` column to users (first 5 games free)
2. **Credits System** - Creates `user_credits` table with sync triggers to existing `mini_word_credits`
3. **Usage Ledger** - `credit_usage` table tracks all credit spending with full audit trail
4. **Word Lessons** - Enhances `words` table with definitions, examples, phonics for learning
5. **Puzzle Coordinates** - `puzzle_words` table maps word positions in grids
6. **User Preferences** - `user_prefs` table for auto-teach, mute settings
7. **Game Sessions** - `game_sessions` table tracks game state and costs
8. **Word Reveals** - `word_reveals` table logs revealed words with lessons
9. **Helper Functions** - `get_user_credits()` and `spend_user_credits()` for atomic operations

### How to run:

```bash
# Set your DATABASE_URL
export DATABASE_URL="postgresql://user:pass@host:port/dbname"

# Run the migration
python run_block_a_migration.py

# Or verify an existing migration
python run_block_a_migration.py --verify-only
```

### Features enabled:
- ✅ 5 free games per user, then 5 credits per game
- ✅ Word reveal costs 5 credits + shows lesson
- ✅ Credit spending with full audit trail
- ✅ Word definitions, examples, and pronunciation
- ✅ User preferences persistence
- ✅ Atomic credit operations with PostgreSQL functions

### Safety:
- Uses `IF NOT EXISTS` for all table creation
- Preserves existing data
- Syncs with existing `mini_word_credits` column
- Can be re-run safely (idempotent)
- Includes verification tests

### Next Steps:
After running this migration, implement:
- Block B: Flask blueprints (`/api/credits`, `/api/game`, `/api/prefs`)
- Block C: Frontend JavaScript for balance display and game flow
- Block D: Lesson overlay with browser TTS
- Block E: Auto-teach system on word discovery