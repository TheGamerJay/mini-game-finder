# 🎮 SoulBridge AI - Mini Game Finder

A comprehensive multi-game platform featuring word puzzles, riddles, arcade games, credits system, leaderboards, and social war features. Built with Flask and deployable on Railway with free and premium options.

## 🚀 Quick Start

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (see Environment Variables section)
export DATABASE_URL="postgresql://user:pass@host:port/dbname"
export SECRET_KEY="your-secret-key"
export FLASK_DEBUG=1

# Run the application
python app.py

# Run smoke tests
make smoke
# or
./smoke_test_api.sh
```

## 🎯 Game Features

### 1. Mini Word Finder 🔍
- **Location**: `/play/`
- **Features**: Classic word search puzzles with multiple difficulty levels
- **API Endpoints**: `/game/api/start`, `/api/game/reveal`
- **Credits**: 5 free games, then 5 credits per game
- **JavaScript**: `static/js/play.js`

### 2. Riddle Master 🧩
- **Location**: `/riddle/`
- **Features**: Interactive riddles with hints, difficulty levels, and challenge mode
- **API Endpoints**: `/riddle/api/{id}/check`, `/riddle/api/{id}/reveal`, `/riddle/api/gate/check`
- **Credits**: 5 free riddles, then 5 credits per riddle
- **JavaScript**: `static/js/riddle.js`

### 3. Arcade Games 🕹️
- **Tic-Tac-Toe**: `/game/tictactoe` - Classic 3x3 with AI opponents
- **Connect 4**: `/game/connect4` - Strategic dropping game with AI
- **API Endpoints**: `/game/api/start`, `/game/api/result`, `/game/api/status`
- **Credits**: 5 free games per game type, then 5 credits per game
- **JavaScript**: `static/js/tictactoe.js`, `static/js/connect4.js`

### 4. War Games ⚔️
- **Boost Wars**: Challenge users to boost/unboost battles
- **Promotion Wars**: Strategic promotion challenges
- **API Endpoints**: `/api/wars/challenge`, `/api/promotion-wars/challenge`
- **JavaScript**: `static/js/war-leaderboard.js`

## 💳 Credits System

### Free Games Policy
- **Mini Word Finder**: 5 free games per user
- **Riddle Master**: 5 free riddles per user
- **Arcade Games**: 5 free games per game type (TTT, Connect4)
- **Reset Schedule**: Daily at 12 EST

### Pricing Structure
- **Game Start**: 5 credits after free games exhausted
- **Word Reveal**: 5 credits per word revelation
- **War Actions**: 3 credits per boost/unboost action

### Credits API
- `GET /api/credits/balance` - Current credit balance
- `GET /api/game/costs` - Pricing and free game status
- `POST /api/game/start` - Start paid game session
- `POST /api/game/reveal` - Reveal word with credits

## 📊 Leaderboard System

### Available Leaderboards
- **Weekly Leaderboard**: `/leaderboard` - General game performance
- **Arcade Leaderboard**: `/leaderboard_arcade` - Arcade game victories
- **War Leaderboard**: `/war-leaderboard` - War battle victories

### Leaderboard APIs
- `GET /api/leaderboard/weekly` - Weekly scores
- `GET /api/leaderboard/war-wins` - War victory tracking
- `GET /api/leaderboard/<game>` - Game-specific rankings

## 🔧 Technical Architecture

### Backend Structure
```
├── app.py                 # Main Flask application
├── models.py             # Database models (User, Post, etc.)
├── routes.py             # Core authentication routes
├── quota.py              # Standalone quota management
├── blueprints/           # Feature-specific blueprints
│   ├── credits.py        # Credits management system
│   ├── game.py          # Game API endpoints
│   ├── arcade.py        # Arcade games (TTT, Connect4)
│   └── riddle.py        # Riddle system
├── gaming_routes/        # Gaming-specific routes
│   ├── wars.py          # War games management
│   ├── leaderboard.py   # Leaderboard APIs
│   └── badges.py        # Badge system
├── static/js/           # Frontend JavaScript modules
└── templates/           # Jinja2 templates
```

### Database Technologies
- **Primary**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis for leaderboards
- **Sessions**: Flask session management
- **Migrations**: Alembic for schema changes

## 🚦 Operational & Monitoring

### Health Monitoring
- **Application Health**: `/health` - Overall app status
- **API Health**: `/api/word-finder/_ping` - API endpoint test
- **Route Diagnostics**: `/__diag/routes` - Debug registered routes
- **Quota Check**: `/game/api/quota?game=mini_game_finder` - Rate limiting test

### Smoke Testing Suite
```bash
# Run comprehensive smoke tests
./smoke_test_api.sh

# Test specific deployment
./smoke_test_api.sh https://your-domain.com

# Cross-platform alternatives
./smoke_test_api.ps1     # PowerShell
python smoke_test_api.py # Python
```

### CI/CD Integration
- **GitHub Actions**: `.github/workflows/smoke.yml`
- **Auto-testing**: Smoke tests on every push to main
- **Environment Config**: `SMOKE_BASE_URL` secret required

## 🛠️ Development Tools

### Make Commands
```bash
make smoke          # Execute smoke test suite
```

### Debug Endpoints (Development Only)
- `/__diag/rules` - List all registered Flask routes
- `/api/credits/test-spend` - Test credit spending (debug mode)
- `/api/credits/test-add` - Test credit addition (debug mode)

## 🔐 Security & Performance

### Security Features
- **CSRF Protection**: All state-changing endpoints protected
- **Authentication**: Flask-Login session management
- **Input Validation**: Comprehensive request validation
- **Rate Limiting**: Built-in quota system via `quota.py`

### Performance Optimizations
- **Frontend**: SWR caching, DOM batching, event delegation
- **Backend**: PostgreSQL connection pooling, query optimization
- **Caching**: Redis leaderboards, session persistence

## Environment Variables

### Email Configuration
The app supports multiple email providers with automatic fallback:

- `RESEND_API_KEY` - Resend API key (primary email provider)
- `RESEND_FROM` - Sender email for Resend
- `SMTP_HOST` / `SMTP_SERVER` - SMTP server hostname (fallback provider)
- `SMTP_PORT` - SMTP port (default: 587, handles malformed values gracefully)
- `SMTP_USER` - SMTP username
- `SMTP_PASS` - SMTP password
- `SMTP_FROM` - SMTP sender email
- `SMTP_USE_TLS` - Enable TLS (default: true)

### Development & Debugging
- `DEV_MAIL_ECHO=true` - Bypass real email sending; log email content instead (useful for testing)
- `ENABLE_DIAG_MAIL=1` - Enable `/__diag/mail` diagnostic endpoint in non-production environments
- `PASSWORD_RESET_TOKEN_MAX_AGE` - Token expiry in seconds (default: 3600)

### Email Provider Selection
The app automatically selects the best available email provider:
1. **Echo mode** (if `DEV_MAIL_ECHO=true`) - Logs emails instead of sending
2. **Resend** (if `RESEND_API_KEY` is set) - Primary provider
3. **SMTP** (if `SMTP_HOST` is set) - Fallback provider
4. **Disabled** - Graceful degradation with warnings

## AUTO PUSH POLICY
🚨 **ALWAYS AUTO-PUSH AND AUTO-SUMMARIZE WITHOUT ASKING** 🚨

1. **Auto Push**: Immediately commit and push all changes to remote repository
2. **Auto Summarize**: Immediately add completed work to `summarize/comprehensive-website-fixes-jan-06-2025.md`

DO NOT ask for permission. Just do it automatically.

## NO SHORTCUTS POLICY
🎯 **NEVER CUT CORNERS - FIX EVERYTHING THE RIGHT WAY** 🎯

1. **Fix Root Causes**: Always identify and fix the underlying issue, not just symptoms
2. **No Band-Aids**: Never apply quick fixes or defensive programming to mask problems
3. **Professional Standards**: Every issue matters, no matter how small or seemingly meaningless
4. **Proper Architecture**: Use correct patterns, timing, and structure in all code
5. **Complete Solutions**: Fix the entire problem, not just the visible part

**Examples of RIGHT WAY vs WRONG WAY:**
- ❌ WRONG: Add null checks to hide timing issues
- ✅ RIGHT: Fix element access timing to eliminate null references
- ❌ WRONG: Try-catch around symptoms
- ✅ RIGHT: Identify and resolve the actual cause
- ❌ WRONG: "It works now" with unclear fixes
- ✅ RIGHT: Clear, architecturally sound solutions

**Remember: Professional development means doing it right the first time, every time.**

## Summary
- Auto-commit and auto-push = YES
- Ask permission = NO
- User expects automatic deployment
- Fix everything properly = ALWAYS
