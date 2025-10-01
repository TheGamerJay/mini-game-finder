// Play page JavaScript - CSP compliant - FORCE CACHE REFRESH OCT 1 2025 12:25PM
// MAJOR UPDATE: Fixed Play Next Game button to force new puzzle generation
// Fixed score submission to include points field for leaderboard
// Browser cache invalidation: force_new parameter added

/* ========= Block D: Flask Session + Meta CSRF + /__diag/whoami =========
   - Uses session cookies (credentials: 'include')
   - Reads CSRF from <meta name="csrf-token" content="{{ csrf_token }}">
   - Auth checks via GET /__diag/whoami { authenticated: bool, ... }
   - Maps spend(reason) => /api/game/hint and /api/game/reveal
   - Gates paid UI (Hint/Reveal/new game after free) when not authenticated
========================================================================= */

/* --- Improved API object with relative paths and better error handling --- */
const API = {
  enabled: true,
  game: 'mini_word_finder',

  csrf() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  },
  headers(extra = {}) {
    const h = { 'Content-Type': 'application/json', ...extra };
    const token = this.csrf();
    if (token) h['X-CSRF-Token'] = token;
    return h;
  },

  async whoami() {
    try {
      const r = await fetch('/__diag/whoami', { credentials: 'include', cache: 'no-store' });
      if (!r.ok) throw new Error(`whoami ${r.status}`);
      return await r.json(); // { authenticated: bool, ... }
    } catch {
      return { authenticated: false };
    }
  },

  async startGameBackend() {
    try {
      const r = await fetch('/api/arcade/start', {
        method: 'POST',
        credentials: 'include',
        headers: this.headers(),
        body: JSON.stringify({ game: this.game })
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
      return await r.json();
    } catch (e) { return { ok: false, error: String(e) }; }
  },

  async spendBackend(amount, reason, extra = {}) {
    const path =
      reason === 'reveal_all' ? '/api/game/reveal' :
      reason === 'reveal'     ? '/api/game/reveal' :
      reason === 'hint'       ? '/api/game/hint'   :
                                '/api/arcade/spend';

    const body = { amount, reason, game: this.game, ...extra };

    try {
      const r = await fetch(path, {
        method: 'POST',
        credentials: 'include',
        headers: this.headers(),
        body: JSON.stringify(body)
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
      return await r.json(); // e.g. { ok:true, credits:number }
    } catch (e) {
      return { ok: false, error: String(e) };
    }
  }
};

/* --- Helper functions for UX polish --- */
// Prevent double charges by disabling buttons during requests
async function safeAction(btn, fn) {
  if (btn.disabled) return;
  btn.disabled = true;
  const originalText = btn.textContent;
  try {
    await fn();
  } catch (error) {
    console.error('Safe action error:', error);
  } finally {
    btn.disabled = false;
    // Restore button text if it was changed during action
    if (btn.textContent !== originalText && !btn.textContent.includes('Sign in')) {
      btn.textContent = originalText;
    }
  }
}

// Keep credits in sync with server responses
function syncCreditsFromServer(json) {
  if (json && typeof json.credits === 'number') {
    // Update any visible credit displays
    const creditElements = document.querySelectorAll('.credits-amount, .credit-amount, #credit-badge .credit-amount');
    creditElements.forEach(el => {
      el.textContent = json.credits.toLocaleString();
    });

    // Update window balance if credits manager exists
    if (window.creditsSystem && window.creditsSystem.credits) {
      window.creditsSystem.credits.updateBalance(json.credits);
    }

    console.log(`[MWF] Credits synced: ${json.credits}`);
  }
}

// Lightweight telemetry for analytics and performance tracking
function sendTelemetry(event, data = {}) {
  // Skip telemetry if disabled or in development
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.log(`[Telemetry] ${event}:`, data);
    return;
  }

  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const payload = {
    event,
    ts: Date.now(),
    game: 'mini_word_finder',
    mode: MODE,
    daily: IS_DAILY,
    ...data
  };

  try {
    // Use sendBeacon for reliability (fires even if page is closing)
    if (navigator.sendBeacon) {
      navigator.sendBeacon('/api/telemetry/wordhunt',
        new Blob([JSON.stringify(payload)], { type: 'application/json' }));
    } else {
      // Fallback to fetch for older browsers
      fetch('/api/telemetry/wordhunt', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: JSON.stringify(payload)
      }).catch(() => {}); // Silent fail for telemetry
    }
  } catch (e) {
    // Silent fail - telemetry should never break the app
    console.debug('[Telemetry] Failed to send:', e);
  }
}

const meta = document.getElementById('meta');
const MODE = meta.dataset.mode;
const IS_DAILY = meta.dataset.daily === '1';
const CATEGORY = meta.dataset.category || '';
let PUZZLE=null, FOUND=new Set(), DOWN=false, path=[], FOUND_CELLS=new Set();
let HINTS_USED = 0; // Track number of hints used in current game

// Set up puzzle ID for credits system
window.CURRENT_PUZZLE_ID = meta.dataset.puzzleId || Math.floor(Math.random() * 1000000);
const walletEl = document.getElementById('wallet');

// ===== LocalStorage state helpers (drop-in) =====
const STORAGE_PREFIX = 'wordgame';
const STORAGE_VERSION = 2; // bump if you change structure

function storageKey() {
  return `${STORAGE_PREFIX}_${MODE}_${IS_DAILY ? 'daily' : 'regular'}`;
}

function safeParse(json) {
  try { return JSON.parse(json); } catch { return null; }
}

function isSameLocalDate(tsA, tsB) {
  const a = new Date(tsA), b = new Date(tsB);
  return a.getFullYear() === b.getFullYear() &&
         a.getMonth() === b.getMonth() &&
         a.getDate() === b.getDate();
}

function validateState(s) {
  if (!s || typeof s !== 'object') return false;
  if (s.__v !== STORAGE_VERSION) return false;
  if (s.mode !== MODE) return false;
  if (typeof s.is_daily !== 'boolean') return false;
  // Minimal shape checks (keep lenient to avoid false negatives)
  if (!s.puzzle || (s.puzzle && typeof s.puzzle !== 'object')) return false;
  if (!Array.isArray(s.found_cells)) return false;
  return true;
}

// Debounced writer to avoid excessive IO
let _saveTimer = null;
function saveGameStateDebounced() {
  clearTimeout(_saveTimer);
  _saveTimer = setTimeout(saveGameState, 200);
}

// Save current session to localStorage
async function saveGameState() {
  if (!PUZZLE) return;

  // Build a compact, serializable state. Adapt fields to your game.
  const gameState = {
    __v: STORAGE_VERSION,
    mode: MODE,
    is_daily: !!IS_DAILY,
    puzzle: {
      puzzle_id: PUZZLE?.puzzle_id ?? window.CURRENT_PUZZLE_ID ?? 'unknown',
      seed: PUZZLE?.seed ?? null,
      // Store the full puzzle data for reconstruction
      grid: PUZZLE.grid,
      words: PUZZLE.words,
      time_limit: PUZZLE.time_limit
    },
    // Use existing globals for found state
    found: Array.from(FOUND || []),
    found_cells: Array.from(FOUND_CELLS || []),
    mistakes: typeof window.MISTAKES === 'number' ? window.MISTAKES : 0,
    started_at: T0 || (T0 = Date.now()),
    updated_at: Date.now()
  };

  const key = storageKey();
  localStorage.setItem(key, JSON.stringify(gameState));
  console.log(`[MWF] Saved → ${key}`, {
    found_cells_count: gameState.found_cells.length,
    puzzle_id: gameState.puzzle.puzzle_id
  });
}

// Load from localStorage with rollover + validation
async function loadGameState() {
  console.log('[MWF] Loading state from localStorage...');
  const key = storageKey();
  const raw = localStorage.getItem(key);
  const parsed = safeParse(raw);

  if (!parsed) {
    console.log('[MWF] No saved state (or corrupted JSON).');
    return null;
  }

  // Daily rollover: invalidate yesterday's state automatically
  if (parsed.is_daily && !isSameLocalDate(parsed.updated_at, Date.now())) {
    console.log('[MWF] Daily puzzle changed — clearing stale state.');
    localStorage.removeItem(key);
    return null;
  }

  if (!validateState(parsed)) {
    console.log('[MWF] Saved state failed validation — clearing.');
    localStorage.removeItem(key);
    return null;
  }

  console.log('[MWF] Loaded saved state:', {
    puzzle_id: parsed.puzzle?.puzzle_id,
    found_cells_count: parsed.found_cells?.length ?? 0
  });
  return parsed;
}

// Optional: clear helper (e.g., when user hits "New Game")
function clearGameState() {
  localStorage.removeItem(storageKey());
  console.log('[MWF] Cleared saved state.');
}

function restoreGameState(gameState) {
  if (!gameState || !gameState.puzzle) {
    console.warn('Invalid game state provided to restoreGameState');
    return;
  }

  PUZZLE = gameState.puzzle;
  FOUND = new Set(gameState.found || []);
  FOUND_CELLS = new Set(gameState.found_cells || []);
  T0 = gameState.started_at;
  LIMIT = gameState.puzzle.time_limit;

  // Render the restored state
  renderGrid(PUZZLE.grid);
  renderWords(PUZZLE.words);

  // Restore found word highlights
  for(const cellKey of FOUND_CELLS) {
    const [r, c] = cellKey.split('-');
    const cell = document.querySelector(`#grid > div[data-r="${r}"][data-c="${c}"]`);
    if(cell) {
      cell.style.background='rgba(34,255,102,0.8)';
      cell.style.borderColor='rgba(34,255,102,1)';
    }
  }

  // Update word list styling for found words
  for(const word of FOUND) {
    const li = document.getElementById('w-'+word);
    if(li){
      li.style.textDecoration='line-through';
      li.style.opacity='0.6';
      li.style.background='rgba(34,255,102,0.2)';
      li.style.borderColor='rgba(34,255,102,0.5)';

      const revealBtn = li.querySelector('.reveal-btn');
      if(revealBtn) {
        revealBtn.style.display = 'none';
      }
    }
  }

  // Restore timer if applicable
  if (LIMIT) {
    const elapsed = Math.floor((Date.now() - T0) / 1000);
    const remaining = Math.max(0, LIMIT - elapsed);
    if (remaining > 0) {
      startTimer(remaining);
    } else {
      finish(false);
      return;
    }
  }

  updateFinishButton();

  // Save game state after revealing a word
  saveGameStateDebounced();
}


function showConfetti(){
  // Show celebration message
  document.getElementById('celebration').style.display = 'block';

  // Create confetti particles
  const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7', '#dda0dd', '#98d8c8'];
  for(let i = 0; i < 100; i++){
    setTimeout(() => {
      const confetti = document.createElement('div');
      confetti.className = 'confetti';
      confetti.style.left = Math.random() * 100 + '%';
      confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
      confetti.style.animationDelay = Math.random() * 2 + 's';
      confetti.style.animationDuration = (Math.random() * 3 + 2) + 's';
      document.body.appendChild(confetti);

      // Remove confetti after animation
      setTimeout(() => confetti.remove(), 5000);
    }, i * 30);
  }
}

function renderGrid(grid){
  const n = grid.length;
  const G = document.getElementById('grid');
  // Make cells bigger and more beautiful
  const cellSize = n <= 10 ? '48px' : n <= 12 ? '42px' : '38px';
  G.style.gridTemplateColumns = `repeat(${n}, ${cellSize})`;
  G.innerHTML = "";
  for(let r=0;r<n;r++){
    for(let c=0;c<n;c++){
      const d=document.createElement('div');
      d.textContent = grid[r][c];
      d.dataset.r=r; d.dataset.c=c;
      d.style.cssText=`
        width:${cellSize};height:${cellSize};
        display:flex;align-items:center;justify-content:center;
        background:rgba(255,255,255,0.1);color:#fff;
        border-radius:8px;user-select:none;cursor:pointer;
        font-weight:600;font-size:18px;
        transition:all 0.2s ease;
        border:2px solid rgba(255,255,255,0.2);
        box-shadow:0 2px 8px rgba(0,0,0,0.2);
      `;
      // Mouse events
      d.addEventListener('mousedown', (e)=>{
        e.preventDefault();
        DOWN=true;
        path=[{r,c}];
        d.style.background='#22ff66';
        d.style.transform='scale(1.05)';
      });
      d.addEventListener('mouseenter', ()=>{
        if(DOWN){
          // Only add to path if it maintains a straight line or is the second cell
          if(path.length === 1 || wouldMaintainStraightLine(path, {r,c})) {
            if(!path.some(p => p.r === r && p.c === c)){
              d.style.background='#22ff66';
              d.style.transform='scale(1.05)';
              path.push({r,c});
            }
          }
        }
      });
      d.addEventListener('mouseup', ()=>{ if(DOWN){ DOWN=false; checkSelection(); }});
      d.addEventListener('mouseleave', ()=>{ if(!DOWN){ d.style.transform='scale(1)'; }});

      // Touch events for mobile
      d.addEventListener('touchstart', (e)=>{
        e.preventDefault();
        DOWN=true;
        path=[{r,c}];
        d.style.background='#22ff66';
        d.style.transform='scale(1.05)';
      }, {passive: false});

      d.addEventListener('touchmove', (e)=>{
        e.preventDefault();
        if(DOWN){
          // Get element under touch point
          const touch = e.touches[0];
          const elementBelow = document.elementFromPoint(touch.clientX, touch.clientY);
          if(elementBelow && elementBelow.dataset.r !== undefined && elementBelow.dataset.c !== undefined){
            const touchR = parseInt(elementBelow.dataset.r);
            const touchC = parseInt(elementBelow.dataset.c);

            // Only add to path if it maintains a straight line or is the second cell
            if(path.length === 1 || wouldMaintainStraightLine(path, {r: touchR, c: touchC})){
              if(!path.some(p => p.r === touchR && p.c === touchC)){
                elementBelow.style.background='#22ff66';
                elementBelow.style.transform='scale(1.05)';
                path.push({r: touchR, c: touchC});
              }
            }
          }
        }
      }, {passive: false});

      d.addEventListener('touchend', (e)=>{
        e.preventDefault();
        if(DOWN){
          DOWN=false;
          checkSelection();
        }
      }, {passive: false});
      G.appendChild(d);
    }
  }
  document.addEventListener('mouseup', ()=>{ if(DOWN){DOWN=false; checkSelection();}});
  // Global touch end for mobile
  document.addEventListener('touchend', ()=>{ if(DOWN){DOWN=false; checkSelection();}}, {passive: false});
}

function renderWords(words){
  const UL=document.getElementById('wordlist'); UL.innerHTML="";
  // Simple authentication check - if credits counter exists, user is logged in
  const isLoggedIn = document.querySelector('.credits-amount') !== null;

  for(const w of words){
    const li=document.createElement('li');
    li.className = 'word-item';
    li.id='w-'+w;
    li.style.cssText=`
      margin:8px 0; padding:8px 12px;
      background:rgba(255,255,255,0.1);
      border-radius:6px; color:white;
      font-weight:500; border:1px solid rgba(255,255,255,0.2);
      transition:all 0.2s ease;
      display:flex; justify-content:space-between; align-items:center;
    `;

    // Word text
    const wordSpan = document.createElement('span');
    wordSpan.textContent = w;
    li.appendChild(wordSpan);

    // Reveal button for logged in users
    if (isLoggedIn) {
      const revealBtn = document.createElement('button');
      revealBtn.className = 'btn reveal-btn';
      revealBtn.dataset.action = 'reveal';
      revealBtn.dataset.puzzleId = window.CURRENT_PUZZLE_ID || PUZZLE?.puzzle_id || '';
      revealBtn.dataset.wordId = w; // Using word as ID for now
      revealBtn.textContent = 'Reveal (5)';
      revealBtn.style.cssText = `
        font-size:12px; padding:4px 8px; margin-left:8px;
        background:rgba(255,255,255,0.2); border:1px solid rgba(255,255,255,0.3);
        color:white; border-radius:4px; cursor:pointer;
      `;
      li.appendChild(revealBtn);
    }

    UL.appendChild(li);
  }
}

function markFound(word){
  FOUND.add(word);

  // Mark current path cells as permanently found
  for(const {r,c} of path){
    FOUND_CELLS.add(`${r}-${c}`);
    const cell = document.querySelector(`#grid > div[data-r="${r}"][data-c="${c}"]`);
    if(cell) {
      cell.style.background='rgba(34,255,102,0.8)';
      cell.style.borderColor='rgba(34,255,102,1)';
      cell.style.transform='scale(1)';
    }
  }

  const li=document.getElementById('w-'+word);
  if(li){
    li.style.textDecoration='line-through';
    li.style.opacity='0.6';
    li.style.background='rgba(34,255,102,0.2)';
    li.style.borderColor='rgba(34,255,102,0.5)';

    // Hide reveal button for found words
    const revealBtn = li.querySelector('.reveal-btn');
    if(revealBtn) {
      revealBtn.style.display = 'none';
    }
  }

  // Trigger auto-teach system
  if (window.autoTeachSystem) {
    window.autoTeachSystem.onWordFound(word);
  }

  updateFinishButton();

  // Save game state after finding a word
  saveGameStateDebounced();
}

// Function specifically for revealed words (doesn't require active path)
function markFoundRevealed(word, wordPath) {
  FOUND.add(word);

  // Mark cells as permanently found if path provided
  if (wordPath && Array.isArray(wordPath)) {
    for(const pos of wordPath){
      const cellKey = `${pos.row}-${pos.col}`;
      FOUND_CELLS.add(cellKey);
      const cell = document.querySelector(`#grid > div[data-r="${pos.row}"][data-c="${pos.col}"]`);
      if(cell) {
        cell.style.background='rgba(34,255,102,0.8)';
        cell.style.borderColor='rgba(34,255,102,1)';
        cell.style.transform='scale(1)';
      }
    }
  }

  // Update word list styling
  const li=document.getElementById('w-'+word);
  if(li){
    li.style.textDecoration='line-through';
    li.style.opacity='0.6';
    li.style.background='rgba(34,255,102,0.2)';
    li.style.borderColor='rgba(34,255,102,0.5)';

    // Hide reveal button for found words
    const revealBtn = li.querySelector('.reveal-btn');
    if(revealBtn) {
      revealBtn.style.display = 'none';
    }
  }

  // Trigger auto-teach system
  if (window.autoTeachSystem) {
    window.autoTeachSystem.onWordFound(word);
  }

  updateFinishButton();

  // Save game state after finding a word
  saveGameStateDebounced();
}

function updateFinishButton(){
  const finishBtn = document.getElementById('finishBtn');
  if(FOUND.size === PUZZLE.words.length){
    finishBtn.disabled = false;
    finishBtn.textContent = '🏆 Submit to Leaderboard';
    finishBtn.style.background = '#22ff66';
    finishBtn.style.color = '#000';
  } else {
    finishBtn.disabled = true;
    finishBtn.textContent = `Find All Words (${FOUND.size}/${PUZZLE.words.length})`;
    finishBtn.style.background = '';
    finishBtn.style.color = '';
  }
}

function wouldMaintainStraightLine(currentPath, newCell) {
  if(currentPath.length < 2) return true; // Always allow second cell

  // Get direction from first two cells
  const dr = Math.sign(currentPath[1].r - currentPath[0].r);
  const dc = Math.sign(currentPath[1].c - currentPath[0].c);

  // Check if new cell maintains the same direction
  const lastCell = currentPath[currentPath.length - 1];
  const newDr = Math.sign(newCell.r - lastCell.r);
  const newDc = Math.sign(newCell.c - lastCell.c);

  return newDr === dr && newDc === dc;
}

function straightLine(cells){
  if(cells.length<2) return false;
  const r = cells.map(c=>c.r), c = cells.map(c=>c.c);
  const dr = Math.sign(r.at(-1)-r[0]), dc = Math.sign(c.at(-1)-c[0]);
  for(let i=1;i<cells.length;i++){
    if(r[i]-r[i-1]!==dr || c[i]-c[i-1]!==dc) return false;
  }
  return true;
}

function checkSelection(){
  const G=[...document.querySelectorAll('#grid > div')];
  const n=Math.sqrt(G.length)|0;
  if(path.length<2) { resetHighlights(); return; }
  if(!straightLine(path)){ resetHighlights(); return; }
  let s="";
  for(const {r,c} of path){ s+=PUZZLE.grid[r][c]; }
  const rev=[...s].reverse().join('');
  let hit=null;
  for(const w of PUZZLE.words){
    if(!FOUND.has(w) && (w===s || w===rev)){ hit=w; break; }
  }
  if(hit){
    markFound(hit);
    if(FOUND.size===PUZZLE.words.length){
      // All words found - show confetti and complete
      showConfetti();
      setTimeout(() => finish(true), 3000); // Give time to enjoy the celebration
    }
  }else{
    resetHighlights();
  }
  path=[];
}
function resetHighlights(){
  document.querySelectorAll('#grid > div').forEach(d=>{
    const r = d.dataset.r;
    const c = d.dataset.c;
    const cellKey = `${r}-${c}`;

    // Only reset if it's not a permanently found cell
    if(!FOUND_CELLS.has(cellKey) && d.style.background==='rgb(34, 255, 102)'){
      d.style.background='rgba(255,255,255,0.1)';
      d.style.transform='scale(1)';
      d.style.borderColor='rgba(255,255,255,0.2)';
    }
  });
}

// Word reveal functionality for credits system
window.markFoundRevealed = markFoundRevealed;

window.highlightWordPath = function(path) {
  if (!path || !Array.isArray(path)) return;

  // Reset any existing highlights
  resetHighlights();

  // Highlight the word path
  path.forEach(pos => {
    const cell = document.querySelector(`#grid > div[data-r="${pos.row}"][data-c="${pos.col}"]`);
    if (cell) {
      cell.style.background = '#ff6b6b';
      cell.style.transform = 'scale(1.05)';
      cell.style.border = '2px solid #ff4757';
    }
  });

  // Auto-remove highlight after 3 seconds, but preserve found cells
  setTimeout(() => {
    path.forEach(pos => {
      const cell = document.querySelector(`#grid > div[data-r="${pos.row}"][data-c="${pos.col}"]`);
      if (cell) {
        const cellKey = `${pos.row}-${pos.col}`;

        // Only reset if this cell is not permanently found
        if (!FOUND_CELLS.has(cellKey)) {
          cell.style.background = 'rgba(255,255,255,0.1)';
          cell.style.transform = 'scale(1)';
          cell.style.border = '2px solid rgba(255,255,255,0.2)';
        } else {
          // Restore found cell appearance
          cell.style.background = 'rgba(34,255,102,0.8)';
          cell.style.borderColor = 'rgba(34,255,102,1)';
          cell.style.transform = 'scale(1)';
        }
      }
    });
  }, 3000);
};

// The lesson overlay functionality is now handled by lesson-overlay.js
// window.showLessonOverlay is available globally

let T0=null, LIMIT=null, TICK=null;
function startTimer(sec){
  const el=document.getElementById('timer');
  if(!sec){
    el.textContent="No timer";
    // Notify auto-teach system about no-timer mode
    if (window.autoTeachSystem) {
      window.autoTeachSystem.setGameContext(MODE, false);
    }
    return;
  }

  // Notify auto-teach system about timer mode
  if (window.autoTeachSystem) {
    window.autoTeachSystem.setGameContext(MODE, true);
  }

  // If T0 and LIMIT are already set (from restored state), use them; otherwise set new ones
  if (!LIMIT || !T0) {
    LIMIT = sec;
    T0 = Date.now();
  }

  el.style.display = 'block';
  TICK=setInterval(()=>{
    const gone = Math.floor((Date.now()-T0)/1000);
    const left = Math.max(0, LIMIT-gone);
    const m = String(Math.floor(left/60)).padStart(1,'0');
    const s = String(left%60).padStart(2,'0');
    el.textContent = `Time: ${m}:${s}`;
    if(left<=0){ clearInterval(TICK); finish(false); }
  }, 250);
}

async function loadPuzzle(){
  // Try to restore saved game first
  const savedState = await loadGameState();
  if (savedState) {
    console.log('Restoring saved game state');
    restoreGameState(savedState);
    return;
  }

  // Check if we have a completed puzzle that we shouldn't reload
  const completedKey = `puzzle_completed_${MODE}_${IS_DAILY ? 'daily' : 'regular'}`;
  const completedPuzzleId = localStorage.getItem(completedKey);

  if (completedPuzzleId) {
    console.log(`Found completed puzzle ${completedPuzzleId}, checking if it's still current...`);
  }

  // Load new puzzle if no saved state
  const q = new URLSearchParams({mode: MODE, daily: IS_DAILY?1:0});
  if (CATEGORY) q.set('category', CATEGORY);
  const res = await fetch(`/api/puzzle?${q}`, { credentials:'include' });
  PUZZLE = await res.json();

  // If this is the same puzzle we completed before, offer to continue to next game
  if (completedPuzzleId && PUZZLE.puzzle_id === completedPuzzleId) {
    console.log('This puzzle was already completed! Offering to continue to next game...');
    showContinueToNextGameInterface();
    return;
  }

  renderGrid(PUZZLE.grid);
  renderWords(PUZZLE.words);
  startTimer(PUZZLE.time_limit);
  updateFinishButton(); // Initialize button state

  // Save initial state
  saveGameState();

  // Track level start
  sendTelemetry('level_start', {
    puzzle_id: PUZZLE.puzzle_id,
    words_count: PUZZLE.words.length,
    grid_size: `${PUZZLE.grid.length}x${PUZZLE.grid[0]?.length || 0}`,
    has_timer: !!PUZZLE.time_limit,
    category: CATEGORY
  });
}

async function finish(completed){
  clearInterval(TICK);

  // Track level completion
  const duration = T0 ? (Date.now() - T0) : 0;
  sendTelemetry('level_complete', {
    puzzle_id: PUZZLE?.puzzle_id,
    completed: completed,
    words_found: FOUND.size,
    total_words: PUZZLE?.words.length || 0,
    duration_ms: duration,
    hints_used: HINTS_USED || 0,
    category: CATEGORY
  });

  // If completed successfully, save completion state to prevent re-showing this puzzle
  if (completed && PUZZLE && PUZZLE.puzzle_id) {
    const completedKey = `puzzle_completed_${MODE}_${IS_DAILY ? 'daily' : 'regular'}`;
    localStorage.setItem(completedKey, PUZZLE.puzzle_id);
    console.log(`Marked puzzle ${PUZZLE.puzzle_id} as completed`);
  }

  // Clear saved game state when finishing
  try {
    const response = await fetch(`/api/game/progress/clear?mode=${MODE}&daily=${IS_DAILY}`, {
      method: 'POST',
      headers: {
        'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
      },
      credentials: 'include'
    });

    if (response.status === 401) {
      console.log('Not authenticated, localStorage will handle clearing');
    } else if (!response.ok) {
      console.warn('Failed to clear progress from database');
    }
  } catch (error) {
    console.warn('Error clearing progress from database:', error);
  }

  // Also clear localStorage as fallback
  localStorage.removeItem(`wordgame_${MODE}_${IS_DAILY ? 'daily' : 'regular'}`);

  // Hide celebration overlay
  document.getElementById('celebration').style.display = 'none';

  // Notify credits system about game completion
  if (window.creditsSystem && window.creditsSystem.game) {
    try {
      await window.creditsSystem.game.completeGame(FOUND.size, PUZZLE.words.length, FOUND.size * 10);
    } catch (error) {
      console.warn('Failed to complete game session:', error);
    }
  }

  const elapsedTime = LIMIT ? (LIMIT - Math.max(0, Math.floor(LIMIT - (Date.now()-T0)/1000))) : Math.floor((Date.now()-T0)/1000);
  const body = {
    mode: MODE, daily: IS_DAILY,
    total_words: PUZZLE.words.length, found_count: FOUND.size,
    duration_sec: elapsedTime, completed: Boolean(completed),
    seed: PUZZLE.seed, category: CATEGORY || null,
    hints_used: HINTS_USED, puzzle_id: PUZZLE.puzzle_id || null
  };
  let scoreResult = null;
  try{
    const response = await fetch('/api/score',{
      method:'POST',
      headers:{
        'Content-Type':'application/json',
        'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
      },
      credentials:'include',
      body: JSON.stringify(body)
    });

    if (response.ok) {
      scoreResult = await response.json();
    }
  }catch(e){
    console.log('Score submission error:', e);
  }

  // Game counter updates automatically via main counter component

  // Show completion dialog instead of alert
  console.log('Calling showCompletionDialog with completed:', completed);
  showCompletionDialog(completed, duration, scoreResult);
}

async function showCompletionDialog(completed, duration, scoreResult) {
  const dialog = document.getElementById('completionDialog');
  const wordsFoundText = document.getElementById('wordsFoundText');
  const timeCompletedText = document.getElementById('timeCompletedText');
  const scoreText = document.getElementById('scoreText');
  const playAgainBtn = document.getElementById('playAgainBtn');

  // Update dialog content
  if (completed) {
    wordsFoundText.textContent = `🎉 Found all ${PUZZLE.words.length} words!`;

    // Show Redis leaderboard rank if available
    let rankText = '🏆 Score submitted to leaderboard!';
    if (scoreResult && scoreResult.redis_leaderboard && scoreResult.redis_leaderboard.ok) {
      const lb = scoreResult.redis_leaderboard;
      if (lb.rank && lb.season_id) {
        rankText = `🏆 Ranked #${lb.rank} this week (${lb.season_id})!`;
        if (lb.rank === 1) {
          rankText = `👑 #1 Champion this week (${lb.season_id})!`;
        } else if (lb.rank <= 3) {
          rankText = `🥇 Top 3 this week! Ranked #${lb.rank} (${lb.season_id})`;
        } else if (lb.rank <= 10) {
          rankText = `🌟 Top 10 this week! Ranked #${lb.rank} (${lb.season_id})`;
        }
      }
    }
    scoreText.textContent = rankText;
  } else {
    wordsFoundText.textContent = `⏰ Time's up! Found ${FOUND.size}/${PUZZLE.words.length} words`;
    scoreText.textContent = '📝 Progress saved!';
  }

  // Format and display time
  const minutes = Math.floor(duration / 60);
  const seconds = duration % 60;
  timeCompletedText.textContent = `⏱️ Time: ${minutes}:${seconds.toString().padStart(2, '0')}`;

  // Check game costs and update Play Again button
  try {
    const response = await fetch('/api/game/costs', { credentials: 'include' });
    const data = await response.json();

    if (data.user && data.user.free_games_remaining > 0) {
      playAgainBtn.textContent = `Play Next Game (${data.user.free_games_remaining} free left)`;
      playAgainBtn.classList.remove('cost-required');
      playAgainBtn.disabled = false;
    } else if (data.user && data.user.balance >= data.costs.game_start) {
      playAgainBtn.textContent = `Play Next Game (${data.costs.game_start} credits)`;
      playAgainBtn.classList.add('cost-required');
      playAgainBtn.disabled = false;
    } else {
      playAgainBtn.textContent = `Need ${data.costs.game_start} credits`;
      playAgainBtn.classList.add('cost-required');
      playAgainBtn.disabled = true;
    }
  } catch (error) {
    console.warn('Failed to fetch game costs:', error);
    playAgainBtn.textContent = 'Play Next Game';
  }

  // Show dialog with flex display
  console.log('Showing completion dialog');
  dialog.style.display = 'flex';
}

function hideCompletionDialog() {
  const dialog = document.getElementById('completionDialog');
  dialog.style.display = 'none';
}

async function playAgain() {
  console.log('playAgain() called');
  const playAgainBtn = document.getElementById('playAgainBtn');

  try {
    // First, check current game status
    const response = await fetch('/api/game/costs', { credentials: 'include' });
    const data = await response.json();

    let confirmMessage;
    let isUsingFreeGame = false;

    if (data.user && data.user.free_games_remaining > 0) {
      // User has free games remaining
      confirmMessage = `Would you like to proceed to the next game?\n\nThis will use 1 of your ${data.user.free_games_remaining} remaining free daily games.`;
      isUsingFreeGame = true;
    } else {
      // User has used all free games, needs credits
      confirmMessage = `Your daily free games have reached their limit for today.\n\nWould you like to proceed? It will cost ${data.costs.game_start} credits per game.\n\nYou have ${data.user.balance} credits.`;

      if (data.user.balance < data.costs.game_start) {
        // Not enough credits
        alert(`You need ${data.costs.game_start} credits to start a new game.\nYou currently have ${data.user.balance} credits.\n\nPlease purchase more credits to continue playing.`);
        return;
      }
    }

    // Show confirmation prompt
    if (!confirm(confirmMessage)) {
      return; // User cancelled
    }

    // Disable button and show loading
    playAgainBtn.disabled = true;
    playAgainBtn.textContent = 'Starting...';

    // Clear any saved state and reload the page to start fresh
    try {
      await fetch(`/api/game/progress/clear?mode=${MODE}&daily=${IS_DAILY}&category=${CATEGORY || ''}`, {
        method: 'POST',
        headers: {
          'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
        },
        credentials: 'include'
      });
    } catch (error) {
      console.warn('Error clearing progress for new game:', error);
    }

    // Clear all localStorage items for this game
    localStorage.removeItem(`wordgame_${MODE}_${IS_DAILY ? 'daily' : 'regular'}`);
    localStorage.removeItem(`puzzle_completed_${MODE}_${IS_DAILY ? 'daily' : 'regular'}`);

    // Add force_new parameter to URL to ensure fresh puzzle generation
    const url = new URL(window.location.href);
    url.searchParams.set('force_new', Date.now());
    window.location.href = url.toString();

  } catch (error) {
    console.error('Error starting new game:', error);
    playAgainBtn.textContent = 'Play Next Game';
    playAgainBtn.disabled = false;
    alert('Failed to start new game. Please try again.');
  }
}

function viewLeaderboard() {
  console.log('viewLeaderboard() called');

  // Open Redis leaderboard in new tab with the current game
  const redisLeaderboardUrl = `/redis-leaderboard?game=mini_word_finder`;
  window.open(redisLeaderboardUrl, '_blank');

  // Also try the legacy leaderboard as fallback
  const legacyUrl = `/api/leaderboard/word-finder/${MODE}`;
  fetch(legacyUrl, { credentials: 'include' })
    .then(response => response.json())
    .then(data => {
      if (data.leaders && data.leaders.length > 0) {
        console.log('Legacy leaderboard data also available:', data);
      }
    })
    .catch(error => {
      console.error('Error fetching leaderboard:', error);
      alert('🏆 Leaderboard: Your score has been submitted! Visit the community section to see rankings.');
    });
}

function backToMenu() {
  window.location.href = '/';
}

// Reset function removed - using daily counter display instead

// Ensure this runs after the DOM exists (safe even if script is at page end)
document.addEventListener('DOMContentLoaded', () => {
  // Cache all elements the script touches
  const meta        = document.getElementById('meta');
  const walletEl    = document.getElementById('wallet');
  const grid        = document.getElementById('grid');
  const wordlist    = document.getElementById('wordlist');   // <-- matches template
  const finishBtn   = document.getElementById('finishBtn');   // <-- added in template
  const timerEl     = document.getElementById('timer');       // <-- added in template
  const celebration = document.getElementById('celebration'); // <-- added in template

  // Helper to safely bind listeners
  const on = (el, ev, fn) => el ? el.addEventListener(ev, fn) : console.warn(`Missing #${ev} target`, el);

  // Finish game handler
  on(finishBtn, 'click', () => {
    if (!finishBtn.disabled) finish(true); // Only allow when all words found
  });

  // Reset button removed - using daily counter instead

  // Completion dialog handlers
  const playAgainBtn = document.getElementById('playAgainBtn');
  const viewLeaderboardBtn = document.getElementById('viewLeaderboardBtn');
  const backToMenuBtn = document.getElementById('backToMenuBtn');

  on(playAgainBtn, 'click', playAgain);
  on(viewLeaderboardBtn, 'click', viewLeaderboard);
  on(backToMenuBtn, 'click', backToMenu);



  // Safety checks - warn about missing elements
  if (!wordlist)  console.warn('Expected #wordlist element is missing.');
  if (!timerEl)   console.warn('Expected #timer element is missing.');
  if (!grid)      console.warn('Expected #grid element is missing.');

  // Optional: show/hide timer via a safe API
  function setTimerText(t) {
    if (!timerEl) return;
    timerEl.textContent = t;
    timerEl.style.display = t ? 'block' : 'none';
  }

  // Load the puzzle
  loadPuzzle();

  // Game counter updates automatically via main counter component
});

/* --- Auth-aware UI gating --- */
(async function authGate(){
  const { authenticated } = await API.whoami();  // Use improved whoami method

  console.log('[MWF] Auth status:', authenticated ? 'authenticated' : 'guest');

  // Store auth status globally for reveal button rendering
  window.IS_AUTHENTICATED = authenticated;

  // Disable reveal buttons for unauthenticated users
  const revealButtons = document.querySelectorAll('[data-action="reveal"], .reveal-btn');
  if (!authenticated) {
    revealButtons.forEach(button => {
      button.disabled = true;
      button.title = 'Sign in to use reveal';
      button.textContent = button.textContent.replace(/Reveal.*/, 'Sign in required');
    });
  }

  // If not authenticated, override reveal functionality in credits manager
  if (!authenticated && window.revealManager) {
    const originalHandleRevealClick = window.revealManager.handleRevealClick.bind(window.revealManager);
    window.revealManager.handleRevealClick = async function(button) {
      button.disabled = true;
      button.textContent = 'Sign in required';
      alert('Please sign in to use the reveal feature.');
      setTimeout(() => {
        button.disabled = false;
        button.textContent = `Reveal (${this.revealCost})`;
      }, 2000);
    };
  }
})();

/* --- Enhanced error handling with re-auth flow --- */
const origSpend = API.spendBackend.bind(API);
API.spendBackend = async (...args) => {
  const res = await origSpend(...args);
  if (!res.ok && String(res.error||'').includes('HTTP 401')) {
    console.log('[MWF] Session expired or not authenticated');
    // Show user-friendly message
    const message = 'Your session expired. Please sign in to continue.';
    if (window.showToast) {
      window.showToast(message);
    } else {
      alert(message);
    }

    // Optional: redirect to login with return URL
    setTimeout(() => {
      window.location.href = '/login?next=' + encodeURIComponent(location.pathname);
    }, 2000);
  }

  // Sync credits on successful responses and track spending
  if (res.ok) {
    syncCreditsFromServer(res);

    // Track successful spend events
    const [amount, reason] = args;
    sendTelemetry('spend', {
      reason: reason,
      amount: amount,
      new_balance: res.credits || 0
    });
  }

  return res;
};

// Auto-save on page hide/unload as a safety net
window.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') saveGameState();
});
window.addEventListener('beforeunload', () => saveGameState());

// Game counter functionality removed - handled by main counter component automatically

function showContinueToNextGameInterface() {
  // Clear the game grid and words list
  document.getElementById('grid').innerHTML = '';
  document.getElementById('wordlist').innerHTML = '';

  // Hide the timer
  document.getElementById('timer').style.display = 'none';

  // Create continue interface
  const gameContent = document.querySelector('.play-game-content');
  if (gameContent) {
    gameContent.innerHTML = `
      <div style="text-align: center; padding: 40px 20px; color: white;">
        <div style="font-size: 48px; margin-bottom: 20px;">🎉</div>
        <h2 style="margin: 0 0 10px 0; color: #22ff66;">Game Complete!</h2>
        <p style="margin: 0 0 30px 0; opacity: 0.8;">You've already completed this puzzle.</p>

        <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
          <button id="continueNextBtn" class="btn primary" style="padding: 12px 24px; font-size: 16px;">
            Continue to Next Game
          </button>
          <button id="backToMenuBtn" class="btn secondary" style="padding: 12px 24px; font-size: 16px;">
            Main Menu
          </button>
        </div>

        <div style="margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px;">
          <p style="margin: 0; font-size: 14px; opacity: 0.7;">
            Ready for your next challenge?
          </p>
        </div>
      </div>
    `;

    // Add event listeners
    document.getElementById('continueNextBtn').addEventListener('click', async () => {
      await startNextGame();
    });

    document.getElementById('backToMenuBtn').addEventListener('click', () => {
      window.location.href = '/';
    });
  }
}

async function startNextGame() {
  try {
    // Clear the completion marker so we get a new puzzle
    const completedKey = `puzzle_completed_${MODE}_${IS_DAILY ? 'daily' : 'regular'}`;
    localStorage.removeItem(completedKey);

    // Clear any saved game state
    try {
      await fetch(`/api/game/progress/clear?mode=${MODE}&daily=${IS_DAILY}`, {
        method: 'POST',
        headers: {
          'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
        },
        credentials: 'include'
      });
    } catch (e) {
      console.log('Progress clear failed, continuing anyway');
    }

    // Reload the page to start fresh
    window.location.reload();
  } catch (error) {
    console.error('Error starting next game:', error);
    alert('Error starting next game. Please try again.');
  }
}