// Play page JavaScript - CSP compliant

const meta = document.getElementById('meta');
const MODE = meta.dataset.mode;
const IS_DAILY = meta.dataset.daily === '1';
const CATEGORY = meta.dataset.category || '';
let PUZZLE=null, FOUND=new Set(), DOWN=false, path=[], HINTS_USED=0, HINT_TOKEN=null;
const HINTS_MAX = parseInt(meta.dataset.hintsMax || '3');
const walletEl = document.getElementById('wallet');
const unlockBtn = document.getElementById('unlockBtn');
const inputEl = document.getElementById('hintInput');
const sendBtn = document.getElementById('sendHint');
const respEl = document.getElementById('hintResp');

function uiLock(){ inputEl.disabled=true; sendBtn.disabled=true; unlockBtn.disabled=false; HINT_TOKEN=null; }
function uiUnlock(){ inputEl.disabled=false; sendBtn.disabled=false; unlockBtn.disabled=true; inputEl.focus(); }

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
  for(const w of words){
    const li=document.createElement('li');
    li.textContent=w; li.id='w-'+w;
    li.style.cssText=`
      margin:8px 0; padding:8px 12px;
      background:rgba(255,255,255,0.1);
      border-radius:6px; color:white;
      font-weight:500; border:1px solid rgba(255,255,255,0.2);
      transition:all 0.2s ease;
    `;
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

let T0=null, LIMIT=null, TICK=null;
function startTimer(sec){
  const el=document.getElementById('timer');
  if(!sec){ el.textContent="No timer"; return; }
  LIMIT=sec; T0=Date.now();
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
  const hintInput   = document.getElementById('hintInput');
  const sendHint    = document.getElementById('sendHint');
  const hintResp    = document.getElementById('hintResp');    // <-- matches template
  const finishBtn   = document.getElementById('finishBtn');   // <-- added in template
  const timerEl     = document.getElementById('timer');       // <-- added in template
  const celebration = document.getElementById('celebration'); // <-- added in template

  // Helper to safely bind listeners
  const on = (el, ev, fn) => el ? el.addEventListener(ev, fn) : console.warn(`Missing #${ev} target`, el);

  // Finish game handler
  on(finishBtn, 'click', () => {
    if (!finishBtn.disabled) finish(true); // Only allow when all words found
  });

  // Unlock hint handler
  on(unlockBtn, 'click', async () => {
    if (HINTS_USED >= HINTS_MAX) { alert('Max hints reached for this puzzle.'); return; }
    const res = await fetch('/api/hint/unlock', {
      method:'POST', headers:{'Content-Type':'application/json'},
      credentials:'include',
      body: JSON.stringify({ used: HINTS_USED })
    });
    const data = await res.json();
    if(!data.ok){
      if(data.error==='insufficient') alert('Not enough credits.');
      else if(data.error==='max_hints') alert('Max hints reached.');
      else if(data.error==='cooldown') {/* optional */}
      return;
    }
    walletEl.textContent = `Wallet: ${data.balance} credits`;
    HINT_TOKEN = data.token;
    uiUnlock();
  });

  sendBtn.addEventListener('click', async ()=>{
    const term = inputEl.value.trim().toUpperCase();
    if(!term){ inputEl.focus(); return; }
    sendBtn.disabled = true;
    const q = {
      token: HINT_TOKEN, term,
      mode: MODE, category: CATEGORY || null, seed: PUZZLE.seed,
      puzzle_id: PUZZLE.puzzle_id || null
    };
    const res = await fetch('/api/hint/ask', { method:'POST', headers:{'Content-Type':'application/json'}, credentials:'include', body: JSON.stringify(q) });
    const data = await res.json();
    if(!data.ok){
      if(data.error==='not_in_puzzle'){
        respEl.innerHTML = `<em>That word isn't in this puzzle. Try one from the list.</em>`;
        sendBtn.disabled=false; return;
      }
      if(data.error==='expired'){
        respEl.textContent = "Hint session expired. Unlock again."; uiLock(); return;
      }
      if(data.error && data.error.endsWith('_refunded')){
        respEl.innerHTML = `<strong>We couldn't generate the hint. Your credit was refunded.</strong>`;
        uiLock(); return;
      }
      respEl.textContent = "Something went wrong."; uiLock(); return;
    }
    const g = data.guidance;
    respEl.innerHTML = `
      <div><strong>${g.word}</strong></div>
      <div>Start at <code>row ${g.start.row}, col ${g.start.col}</code>; move <strong>${g.direction}</strong> ${g.arrow} for <strong>${g.length}</strong> letters.</div>
    `;
    HINTS_USED++;
    uiLock();
  });

  // Send hint handler
  on(sendHint, 'click', () => {
    const term = hintInput ? hintInput.value.trim().toUpperCase() : '';
    if (!term) {
      if (hintInput) hintInput.focus();
      return;
    }
    // Your existing hint logic here
    if (sendHint) sendHint.disabled = true;
    // Rest of hint sending code...
  });

  // Safety checks - warn about missing elements
  if (!wordlist)  console.warn('Expected #wordlist element is missing.');
  if (!hintResp)  console.warn('Expected #hintResp element is missing.');
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