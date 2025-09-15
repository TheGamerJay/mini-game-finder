# 🎯 Mini Word Finder - Complete Setup Guide

This guide will help you set up the complete database-aware word puzzle system with AI hints, pre-generated templates, and category-based gameplay.

## 🚀 Quick Start

### 1. Environment Setup

Create a `.env` file or set these environment variables:

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:port/database
SECRET_KEY=your-secret-key-here

# AI Hints (Optional but Recommended)
OPENAI_API_KEY=your-openai-api-key
HINT_MODEL=gpt-4o-mini
HINT_CREDIT_COST=1
HINTS_PER_PUZZLE=3
HINT_LLM_MAX_TOKENS=60
HINT_ASSISTANT_NAME=Word Cipher

# Optional Customization
APP_NAME=Mini Word Finder
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Migration

Run the migration script to create/update database tables:

```bash
python migrate_db.py
```

## 📊 Content Setup (Database-Aware Puzzles)

### Step 1: Import Word Dictionary & Categories

```bash
# Import words with categories
python import_words.py dictionary.txt --categories categories.csv --banned banned.txt
```

**Files needed:**
- `dictionary.txt` - One word per line (we've included a sample)
- `categories.csv` - Format: `word,category` (comprehensive sample included)
- `banned.txt` - Words to exclude (optional)

**Sample categories.csv format:**
```csv
LION,animals
PIZZA,food
SOCCER,sports
LAPTOP,technology
```

### Step 2: Generate Pre-built Puzzle Templates

```bash
# Generate 50 puzzles per category/mode combination
python generate_templates_db.py --per-mode 50

# Generate more puzzles for variety
python generate_templates_db.py --per-mode 150

# Generate for specific categories only
python generate_templates_db.py --per-mode 50 --categories animals food sports
```

This creates thousands of ready-to-play puzzles in your `puzzle_bank` table.

## 🎮 How the System Works

### Game Flow
1. **User selects category & mode** → `animals + easy`
2. **System picks puzzle** → Database template OR procedural generation
3. **User plays** → Interactive word-search grid
4. **AI hints available** → Credit-based hint system
5. **Score saved** → Leaderboards and statistics

### Database-Aware Features
- **Category-specific words**: Animals category uses actual animal names
- **Smart word selection**: Appropriate difficulty and length
- **Pre-generated templates**: Zero wait time, unlimited variety
- **Fallback system**: Works even without database content

### AI Hint System
- **Personalized assistant**: Customizable AI personality
- **Credit-based**: Prevents spam, adds value
- **Context-aware**: Understands puzzle layout and word location
- **Fallback support**: Works without OpenAI API

## 🏗 System Architecture

### Core Components

**Frontend:**
- `templates/index.html` - Category selection & game mode chooser
- `templates/play.html` - Interactive puzzle game with hints
- `templates/base.html` - Dark theme with navigation

**Backend:**
- `app.py` - Flask app with authentication
- `routes.py` - Game API endpoints and hint system
- `models.py` - Database models and relationships
- `puzzles.py` - Database-aware puzzle generation

**AI & Content:**
- `llm_hint.py` - OpenAI integration for intelligent hints
- `services/credits.py` - Credit transaction management
- Database tables for words, categories, and pre-built puzzles

### Database Schema

**Core Tables:**
- `users` - User accounts, credits, profile info
- `scores` - Game results, completion times, hints used
- `credit_txns` - Credit transactions with idempotency

**Content Tables:**
- `words` - Master word dictionary with metadata
- `categories` - Game themes (animals, food, sports, etc.)
- `word_categories` - Word-to-category mappings
- `puzzle_bank` - Pre-generated puzzle templates
- `puzzle_plays` - User play history to avoid repeats

## 🎯 Advanced Features

### Credit System
- **Secure transactions**: Idempotency keys prevent double-charging
- **Spend/refund logic**: Context managers for safe operations
- **Admin controls**: Grant credits, adjust balances

### Hint System
- **Session-based tokens**: Secure, time-limited hint unlocks
- **Intelligent responses**: AI understands puzzle context
- **Fallback gracefully**: Works without API key

### Puzzle System
- **Category-aware**: Real animal names for animal puzzles
- **Difficulty scaling**: Word length matches grid size
- **Template recycling**: Avoids showing same puzzle twice
- **Daily puzzles**: Special seeds for consistent daily challenges

## 🔧 Customization

### Adding New Categories

1. **Update categories.csv**:
   ```csv
   GUITAR,music
   PIANO,music
   VIOLIN,music
   ```

2. **Re-import words**:
   ```bash
   python import_words.py dictionary.txt --categories categories.csv
   ```

3. **Generate templates**:
   ```bash
   python generate_templates_db.py --per-mode 30 --categories music
   ```

4. **Update frontend** (templates/index.html):
   ```html
   <option value="music">Music</option>
   ```

### Customizing AI Assistant

Change the AI personality by setting environment variables:

```bash
HINT_ASSISTANT_NAME="Puzzle Master"
HINT_MODEL=gpt-4o-mini
HINT_LLM_MAX_TOKENS=80
```

The assistant will introduce itself with the custom name and adjust response style.

### Adjusting Game Difficulty

Edit `puzzles.py` MODE_CONFIG:

```python
MODE_CONFIG = {
    "easy": {"size": 10, "words": 5, "time": None},
    "medium": {"size": 12, "words": 7, "time": 120},
    "hard": {"size": 14, "words": 10, "time": 180},
    "expert": {"size": 16, "words": 12, "time": 240},  # New mode
}
```

## 🚨 Troubleshooting

### Database Issues
- **Migration fails**: Check DATABASE_URL format
- **No puzzles generated**: Verify categories.csv and word imports
- **Slow queries**: Add database indexes if needed

### AI Hints Not Working
- **Check API key**: Verify OPENAI_API_KEY is set
- **Model issues**: Try different HINT_MODEL (gpt-3.5-turbo, gpt-4o-mini)
- **No credits**: Users need credits to unlock hints

### Content Issues
- **Empty categories**: Ensure words are properly imported and categorized
- **Repeated puzzles**: Generate more templates with higher --per-mode
- **Wrong difficulty**: Check word lengths match MODE_CONFIG

## 📈 Scaling & Performance

### Production Optimization
- **Database indexing**: Add indexes on frequently queried columns
- **Template pre-generation**: Run large batch generation during off-peak hours
- **CDN**: Use CDN for static assets
- **Caching**: Cache puzzle templates and word lists

### Monitoring
- **Track hint usage**: Monitor credit consumption patterns
- **Monitor puzzle quality**: Check word placement success rates
- **User engagement**: Track completion rates by category/difficulty

## 🎉 You're All Set!

Your Mini Word Finder now has:
- ✅ Database-aware category-based puzzles
- ✅ AI-powered hint system with credit management
- ✅ Pre-generated puzzle templates for instant play
- ✅ Modern dark UI with responsive design
- ✅ Complete user management and authentication
- ✅ Terms of Service and Privacy Policy pages

**Test the system:**
1. Register a new account
2. Select a category (animals, food, etc.)
3. Play a puzzle and try the hint system
4. Check that categories show relevant words

**Add content:**
- Import larger word dictionaries
- Generate thousands of puzzle templates
- Add new categories as needed

Enjoy building word puzzles! 🧩✨