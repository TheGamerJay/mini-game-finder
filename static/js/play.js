// Play page JavaScript - CSP compliant

const meta = document.getElementById('meta');
const MODE = meta.dataset.mode;
const IS_DAILY = meta.dataset.daily === '1';
const CATEGORY = meta.dataset.category || '';
let PUZZLE=null, FOUND=new Set(), DOWN=false, path=[];

// Set up puzzle ID for credits system
window.CURRENT_PUZZLE_ID = meta.dataset.puzzleId || Math.floor(Math.random() * 1000000);
const walletEl = document.getElementById('wallet');


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
      d.addEventListener('mousedown', ()=>{DOWN=true; path=[{r,c}]; d.style.background='#22ff66'; d.style.transform='scale(1.05)';});
      d.addEventListener('mouseenter', ()=>{ if(DOWN){ d.style.background='#22ff66'; d.style.transform='scale(1.05)'; path.push({r,c}); }});
      d.addEventListener('mouseup', ()=>{ if(DOWN){ DOWN=false; checkSelection(); }});
      d.addEventListener('mouseleave', ()=>{ if(!DOWN){ d.style.transform='scale(1)'; }});
      G.appendChild(d);
    }
  }
  document.addEventListener('mouseup', ()=>{ if(DOWN){DOWN=false; checkSelection();}});
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
    if(d.style.background==='rgb(34, 255, 102)'){
      d.style.background='rgba(255,255,255,0.1)';
      d.style.transform='scale(1)';
    }
  });
}

// Word reveal functionality for credits system
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

  // Auto-remove highlight after 3 seconds
  setTimeout(() => {
    path.forEach(pos => {
      const cell = document.querySelector(`#grid > div[data-r="${pos.row}"][data-c="${pos.col}"]`);
      if (cell) {
        cell.style.background = 'rgba(255,255,255,0.1)';
        cell.style.transform = 'scale(1)';
        cell.style.border = '2px solid rgba(255,255,255,0.2)';
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

  LIMIT=sec; T0=Date.now();
  el.style.display = 'block';
  TICK=setInterval(()=>{
    const gone = Math.floor((Date.now()-T0)/1000);
    const left = Math.max(0, sec-gone);
    const m = String(Math.floor(left/60)).padStart(1,'0');
    const s = String(left%60).padStart(2,'0');
    el.textContent = `Time: ${m}:${s}`;
    if(left<=0){ clearInterval(TICK); finish(false); }
  }, 250);
}

async function loadPuzzle(){
  const q = new URLSearchParams({mode: MODE, daily: IS_DAILY?1:0});
  if (CATEGORY) q.set('category', CATEGORY);
  const res = await fetch(`/api/puzzle?${q}`, { credentials:'include' });
  PUZZLE = await res.json();
  renderGrid(PUZZLE.grid);
  renderWords(PUZZLE.words);
  startTimer(PUZZLE.time_limit);
  updateFinishButton(); // Initialize button state
}

async function finish(completed){
  clearInterval(TICK);

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

  const message = completed ?
    `🎉 Amazing! You found all ${PUZZLE.words.length} words! Score saved.` :
    "Time's up! Score saved.";
  alert(message);
  location.href = "/";
}

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

});