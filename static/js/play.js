// Play page JavaScript - CSP compliant - FORCE CACHE REFRESH SEPT 21 2025 11:40AM
// MAJOR UPDATE: Removed updateDailyCounter function completely
// Fixed all API endpoint issues and removed unnecessary calls
// Browser cache invalidation: updateDailyCounter removed permanently

const meta = document.getElementById('meta');
const MODE = meta.dataset.mode;
const IS_DAILY = meta.dataset.daily === '1';
const CATEGORY = meta.dataset.category || '';
let PUZZLE=null, FOUND=new Set(), DOWN=false, path=[], FOUND_CELLS=new Set();
let HINTS_USED = 0; // Track number of hints used in current game

// Set up puzzle ID for credits system
window.CURRENT_PUZZLE_ID = meta.dataset.puzzleId || Math.floor(Math.random() * 1000000);
const walletEl = document.getElementById('wallet');

// Game state management
async function saveGameState() {
  if (!PUZZLE) return;

  const gameState = {
    puzzle: PUZZLE,
    found: Array.from(FOUND),
    found_cells: Array.from(FOUND_CELLS),
    mode: MODE,
    daily: IS_DAILY,
    category: CATEGORY,
    start_time: T0,
    time_limit: LIMIT,
    timestamp: Date.now()
  };

  // Save to localStorage (reliable and works for all users)
  const key = `wordgame_${MODE}_${IS_DAILY ? 'daily' : 'regular'}`;
  localStorage.setItem(key, JSON.stringify(gameState));
  console.log(`Game state saved to localStorage with key: ${key}`, {
    found_count: gameState.found.length,
    found_cells_count: gameState.found_cells.length,
    puzzle_id: gameState.puzzle?.puzzle_id || 'unknown'
  });
}

async function loadGameState() {
  try {
    console.log('Loading game state from localStorage...');

    // Fallback to localStorage
    const key = `wordgame_${MODE}_${IS_DAILY ? 'daily' : 'regular'}`;
    console.log(`Looking for localStorage key: ${key}`);

    const saved = localStorage.getItem(key);

    if (!saved) {
      console.log('No saved game state found in localStorage');
      // Debug: show all localStorage keys
      console.log('All localStorage keys:', Object.keys(localStorage));
      return null;
    }

    const gameState = JSON.parse(saved);
    console.log('Found saved game state in localStorage:', {
      found_count: gameState.found?.length || 0,
      found_cells_count: gameState.found_cells?.length || 0,
      puzzle_id: gameState.puzzle?.puzzle_id || 'unknown',
      timestamp: new Date(gameState.timestamp).toLocaleString()
    });

    // Check if saved game is from today (for daily games) or within last 6 hours (for regular games)
    const maxAge = IS_DAILY ? 24 * 60 * 60 * 1000 : 6 * 60 * 60 * 1000; // 24h for daily, 6h for regular
    const age = Date.now() - gameState.timestamp;

    if (age > maxAge) {
      console.log('Game state expired, removing');
      localStorage.removeItem(key);
      return null;
    }

    console.log('Game state is valid, restoring from localStorage');
    return gameState;
  } catch (e) {
    console.warn('Failed to load game state:', e);
    return null;
  }
}

function restoreGameState(gameState) {
  if (!gameState || !gameState.puzzle) {
    console.warn('Invalid game state provided to restoreGameState');
    return;
  }

  PUZZLE = gameState.puzzle;
  FOUND = new Set(gameState.found || []);
  // Handle both old (foundCells) and new (found_cells) format
  FOUND_CELLS = new Set(gameState.found_cells || gameState.foundCells || []);
  // Handle both old (startTime) and new (start_time) format
  T0 = gameState.start_time || gameState.startTime;
  // Handle both old (timeLimit) and new (time_limit) format
  LIMIT = gameState.time_limit || gameState.timeLimit;

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
  saveGameState();
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
  const isLoggedIn = document.querySelector('#credit-badge, #wallet') !== null ||
                    document.body.dataset.authenticated === 'true';

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
  saveGameState();
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
  saveGameState();
}

function updateFinishButton(){
  const finishBtn = document.getElementById('finishBtn');
  if(FOUND.size === PUZZLE.words.length){
    finishBtn.disabled = false;
    finishBtn.textContent = 'Complete Puzzle!';
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

  // If this is the same puzzle we completed before, show completion immediately
  if (completedPuzzleId && PUZZLE.puzzle_id === completedPuzzleId) {
    console.log('This puzzle was already completed! Showing completion screen...');
    // Load the puzzle but mark it as immediately completed
    renderGrid(PUZZLE.grid);
    renderWords(PUZZLE.words);

    // Mark all words as found
    FOUND = new Set(PUZZLE.words);
    FOUND_CELLS = new Set(); // We don't need to highlight cells for pre-completed puzzles

    // Update visuals for completed state
    PUZZLE.words.forEach(word => {
      const li = document.getElementById('w-' + word);
      if (li) {
        li.style.textDecoration = 'line-through';
        li.style.opacity = '0.6';
        li.style.background = 'rgba(34,255,102,0.2)';
        li.style.borderColor = 'rgba(34,255,102,0.5)';

        const revealBtn = li.querySelector('.reveal-btn');
        if (revealBtn) {
          revealBtn.style.display = 'none';
        }
      }
    });

    updateFinishButton();
    setTimeout(() => finish(true), 1000); // Auto-complete after 1 second
    return;
  }

  renderGrid(PUZZLE.grid);
  renderWords(PUZZLE.words);
  startTimer(PUZZLE.time_limit);
  updateFinishButton(); // Initialize button state

  // Save initial state
  saveGameState();
}

async function finish(completed){
  clearInterval(TICK);

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

  const duration = LIMIT ? (LIMIT - Math.max(0, Math.floor(LIMIT - (Date.now()-T0)/1000))) : Math.floor((Date.now()-T0)/1000);
  const body = {
    mode: MODE, is_daily: IS_DAILY,
    total_words: PUZZLE.words.length, found_count: FOUND.size,
    duration_sec: duration, completed: Boolean(completed),
    seed: PUZZLE.seed, category: CATEGORY || null,
    hints_used: HINTS_USED, puzzle_id: PUZZLE.puzzle_id || null
  };
  try{ await fetch('/api/score',{method:'POST', headers:{'Content-Type':'application/json'}, credentials:'include', body: JSON.stringify(body)}); }catch(e){}

  // Game counter updates automatically via main counter component

  // Show completion dialog instead of alert
  showCompletionDialog(completed, duration);
}

async function showCompletionDialog(completed, duration) {
  const dialog = document.getElementById('completionDialog');
  const wordsFoundText = document.getElementById('wordsFoundText');
  const timeCompletedText = document.getElementById('timeCompletedText');
  const scoreText = document.getElementById('scoreText');
  const playAgainBtn = document.getElementById('playAgainBtn');

  // Update dialog content
  if (completed) {
    wordsFoundText.textContent = `🎉 Found all ${PUZZLE.words.length} words!`;
    scoreText.textContent = '✅ Score saved!';
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
      playAgainBtn.textContent = `Play Again (${data.user.free_games_remaining} free left)`;
      playAgainBtn.classList.remove('cost-required');
      playAgainBtn.disabled = false;
    } else if (data.user && data.user.balance >= data.costs.game_start) {
      playAgainBtn.textContent = `Play Again (${data.costs.game_start} credits)`;
      playAgainBtn.classList.add('cost-required');
      playAgainBtn.disabled = false;
    } else {
      playAgainBtn.textContent = `Need ${data.costs.game_start} credits`;
      playAgainBtn.classList.add('cost-required');
      playAgainBtn.disabled = true;
    }
  } catch (error) {
    console.warn('Failed to fetch game costs:', error);
    playAgainBtn.textContent = 'Play Again';
  }

  // Show dialog with flex display
  dialog.style.display = 'flex';
}

function hideCompletionDialog() {
  const dialog = document.getElementById('completionDialog');
  dialog.style.display = 'none';
}

async function playAgain() {
  const playAgainBtn = document.getElementById('playAgainBtn');

  // Disable button and show loading
  playAgainBtn.disabled = true;
  playAgainBtn.textContent = 'Starting...';

  try {
    // Use the credits system to start a new game
    if (window.creditsSystem && window.creditsSystem.game) {
      const gameData = {
        mode: MODE,
        daily: IS_DAILY,
        category: CATEGORY || null
      };

      const result = await window.creditsSystem.game.startGame(gameData);

      if (result.success) {
        // Clear any saved state and reload the page to start fresh
        try {
          await fetch(`/api/game/progress/clear?mode=${MODE}&daily=${IS_DAILY}`, {
            method: 'POST',
            headers: {
              'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
            },
            credentials: 'include'
          });
        } catch (error) {
          console.warn('Error clearing progress for new game:', error);
        }
        localStorage.removeItem(`wordgame_${MODE}_${IS_DAILY ? 'daily' : 'regular'}`);
        location.reload();
      } else {
        // Handle insufficient credits
        if (result.error === 'INSUFFICIENT_CREDITS') {
          playAgainBtn.textContent = `Need ${result.required} credits`;
          playAgainBtn.disabled = true;

          // Show credits needed message
          setTimeout(() => {
            alert(`You need ${result.required} credits to play again. Visit the Store to purchase credits.`);
          }, 100);
        } else {
          playAgainBtn.textContent = 'Play Again';
          playAgainBtn.disabled = false;
          alert('Failed to start new game. Please try again.');
        }
      }
    } else {
      // Fallback: just reload if credits system not available
      localStorage.removeItem(`wordgame_${MODE}_${IS_DAILY ? 'daily' : 'regular'}`);
      location.reload();
    }
  } catch (error) {
    console.error('Error starting new game:', error);
    playAgainBtn.textContent = 'Play Again';
    playAgainBtn.disabled = false;
    alert('Failed to start new game. Please try again.');
  }
}

function backToMenu() {
  location.href = '/';
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
  const backToMenuBtn = document.getElementById('backToMenuBtn');

  on(playAgainBtn, 'click', playAgain);
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

// Game counter functionality removed - handled by main counter component automatically