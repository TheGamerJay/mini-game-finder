# 🐍 Block B - Flask API Blueprints

This directory contains the Flask blueprints that implement the Credits System APIs.

## Blueprints

### 1. Credits API (`/api/credits`)
**File**: `credits.py`

- `GET /api/credits/balance` - Get user's current credit balance
- `GET /api/credits/history` - Get credit usage history with pagination
- `POST /api/credits/test-spend` - Test credit spending (development only)
- `POST /api/credits/test-add` - Test credit addition (development only)

**Functions**:
- `spend_credits(user_id, amount, reason, puzzle_id, word_id)` - Atomic credit spending
- `add_credits(user_id, amount, reason)` - Add credits to balance

### 2. Game API (`/api/game`)
**File**: `game.py`

- `POST /api/game/start` - Start game (free for first 5, then 5 credits)
- `POST /api/game/reveal` - Reveal word with lesson (5 credits)
- `POST /api/game/session/<id>/complete` - Mark game session complete
- `GET /api/game/sessions` - Get user's recent game sessions
- `GET /api/game/costs` - Get current costs and user's free game status

**Game Flow**:
1. User starts game → checks free games remaining or charges credits
2. During game → user can reveal words for 5 credits each
3. Game completion → records final score and session data

### 3. Preferences API (`/api/prefs`)
**File**: `prefs.py`

- `GET /api/prefs/get` - Get preferences (all or specific key)
- `POST /api/prefs/set` - Set a single preference
- `POST /api/prefs/set-multiple` - Set multiple preferences at once
- `POST /api/prefs/reset` - Reset preferences to defaults
- `GET /api/prefs/schema` - Get valid preference keys and defaults

**Valid Preferences**:
- `auto_teach_no_timer` - Auto-teach in no-timer mode (default: true)
- `auto_teach_timer` - Auto-teach in timer mode (default: false)
- `speak_enabled` - Text-to-speech enabled (default: true)
- `lesson_auto_close` - Auto-close lesson overlays (default: false)
- `reveal_confirmation` - Confirm before revealing words (default: true)
- `game_sound_effects` - Sound effects in game (default: true)
- `theme` - UI theme preference (default: default)
- `language` - Language preference (default: en)

## Environment Variables

Add these to your `.env` file:

```bash
# Credits System Configuration
LEARN_MODE_ENABLED=true
REVEAL_WITH_LESSON_ENABLED=true
AUTO_TEACH_ON_FIND_DEFAULT_NO_TIMER=true
AUTO_TEACH_ON_FIND_DEFAULT_TIMER=false
GAME_COST=5
REVEAL_COST=5
FREE_GAMES_LIMIT=5
```

## Authentication

All endpoints use the existing authentication system:
- Session-based auth (primary): `get_session_user()`
- Flask-Login fallback: `current_user.is_authenticated`
- CSRF protection: `@require_csrf` decorator on state-changing endpoints

## Database Integration

- Uses raw PostgreSQL connections for atomic credit operations
- Syncs with existing `users.mini_word_credits` column
- Leverages PostgreSQL functions from Block A migration:
  - `get_user_credits(user_id)` - Get current balance
  - `spend_user_credits(user_id, amount, reason, puzzle_id, word_id)` - Atomic spending

## Error Handling

**Common HTTP Status Codes**:
- `200` - Success
- `401` - Not authenticated
- `402` - Insufficient credits
- `400` - Bad request (missing parameters)
- `404` - Resource not found
- `500` - Server error

**Credit Errors**:
```json
{
  "ok": false,
  "error": "INSUFFICIENT_CREDITS",
  "required": 5,
  "message": "You need 5 credits to start a game. Visit the Store to purchase credits."
}
```

## Usage Examples

### Start a Game
```javascript
const response = await fetch('/api/game/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ puzzle_id: 123, mode: 'easy' })
});

const data = await response.json();
// { ok: true, paid: false, session_id: 456, balance: 100, free_games_remaining: 4 }
```

### Reveal a Word
```javascript
const response = await fetch('/api/game/reveal', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ puzzle_id: 123, word_id: 789 })
});

const data = await response.json();
// { ok: true, balance: 95, path: {...}, lesson: {...} }
```

### Get Credit Balance
```javascript
const response = await fetch('/api/credits/balance', { credentials: 'include' });
const data = await response.json();
// { ok: true, balance: 95, user_id: 123 }
```

### Set Preferences
```javascript
await fetch('/api/prefs/set', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ key: 'speak_enabled', value: false })
});
```

## Integration with Frontend

These APIs are designed to work with:
- **Block C**: Frontend JavaScript for balance display and game flow
- **Block D**: Lesson overlay with TTS pronunciation
- **Block E**: Auto-teach system on word discovery

## Testing

Development endpoints available when `app.debug = True`:
- `POST /api/credits/test-spend` - Test spending credits
- `POST /api/credits/test-add` - Test adding credits

## Next Steps

After implementing Block B, proceed to:
1. **Block C**: Frontend JavaScript integration
2. **Block D**: Lesson overlay UI with browser TTS
3. **Block E**: Auto-teach system implementation