// Connect 4 Game Logic - moved from inline script for CSP compliance

(function(){
  const COLS=7, ROWS=6;
  const boardEl = document.getElementById("c4Board");
  const statusEl = document.getElementById("c4Status");
  const resetBtn = document.getElementById("c4Reset");
  const modeSel = document.getElementById("c4Mode");
  const colorChoiceSel = document.getElementById("colorChoice");
  const colorChoiceLabel = document.getElementById("colorChoiceLabel");

  let grid, turn, over, started, humanPlayer, cpuPlayer;

  async function beginRound(){
    try{
      const r = await fetch("/game/api/start", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ game: "c4" })
      });
      const d = await r.json();
      if (!d.ok){
        if (d.error === "insufficient_credits"){
          setStatus(`Out of credits for extra plays. Need ${5} credits.`);
        } else {
          setStatus("Unable to start. Please reload.");
        }
        disable(); return false;
      }
      const note = d.charged ? `-${d.charged} credits` : `free`;
      setStatus(`Round started (${note}). Free plays left: ${d.free_remaining}. Credits: ${d.credits}.`);
      started = true; return true;
    }catch{ setStatus("Network error."); disable(); return false; }
  }

  function setStatus(t){ statusEl.textContent = t; }
  function disable(){ boardEl.querySelectorAll(".c4-col").forEach(c=>c.classList.add("disabled")); }

  async function reportResult(won){
    try{ await fetch("/game/api/result", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ game:"c4", won: !!won })
    }); }catch{}
  }

  async function init(){
    // Show/hide color choice based on mode
    if (modeSel.value === "cpu") {
      colorChoiceLabel.style.display = "inline-block";
      humanPlayer = parseInt(colorChoiceSel.value);
      cpuPlayer = humanPlayer === 1 ? 2 : 1;
    } else {
      colorChoiceLabel.style.display = "none";
      humanPlayer = 1;
      cpuPlayer = 2;
    }

    grid = Array.from({length: ROWS}, () => Array(COLS).fill(0)); turn=1; over=false; started=false;
    render();
    setStatus("Starting round…");
    const ok = await beginRound();
    if (ok) {
      if (modeSel.value === "cpu") {
        const playerColor = turn === 1 ? "Red" : "Yellow";
        setStatus(turn === humanPlayer ? "Your turn (" + playerColor + ")" : "CPU's turn (" + playerColor + ")");
        if (turn === cpuPlayer) setTimeout(aiMove, 500);
      } else {
        setStatus("Player 1's turn (Red)");
      }
    }
  }

  function render(){
    boardEl.innerHTML = "";
    for (let x=0;x<COLS;x++){
      const col = document.createElement("div");
      col.className = "c4-col"; col.dataset.x = x;
      col.addEventListener("click", onCol);
      for (let y=0;y<ROWS;y++){
        const slot = document.createElement("div");
        slot.className = "c4-slot";
        const p = grid[y][x];
        if (p) slot.dataset.player = String(p);
        col.appendChild(slot);
      }
      boardEl.appendChild(col);
    }
  }

  function onCol(e){
    if (over || !started) return;
    // In CPU mode, only allow human moves
    if (modeSel.value === "cpu" && turn !== humanPlayer) return;

    const x = Number(e.currentTarget.dataset.x);
    if (makeMove(x)) {
      const w = winnerAt(grid);
      if (w){ endGame(w === humanPlayer); return; }
      if (isFull()){ endGame(false); return; }
      turn = (turn===1)?2:1;
      const playerColor = turn === 1 ? "Red" : "Yellow";

      if (modeSel.value === "cpu") {
        const playerName = turn === humanPlayer ? "Your" : "CPU's";
        setStatus(`${playerName} turn (${playerColor})`);
        if (turn === cpuPlayer) setTimeout(aiMove, 500);
      } else {
        setStatus(`Player ${turn}'s turn (${playerColor})`);
      }
    }
  }

  function makeMove(x) {
    for (let y=ROWS-1; y>=0; y--){
      if (grid[y][x] === 0){
        grid[y][x] = turn;
        render();
        return true;
      }
    }
    return false;
  }

  function aiMove(){
    if (over || !started) return;

    // Try to win first
    let col = findWinningMove(cpuPlayer);
    if (col !== -1) {
      makeMove(col);
      const w = winnerAt(grid);
      if (w){ endGame(w === humanPlayer); return; }
      if (isFull()){ endGame(false); return; }
      turn = humanPlayer;
      const playerColor = turn === 1 ? "Red" : "Yellow";
      setStatus(`Your turn (${playerColor})`);
      return;
    }

    // Block human from winning
    col = findWinningMove(humanPlayer);
    if (col !== -1) {
      makeMove(col);
      const w = winnerAt(grid);
      if (w){ endGame(w === humanPlayer); return; }
      if (isFull()){ endGame(false); return; }
      turn = humanPlayer;
      const playerColor = turn === 1 ? "Red" : "Yellow";
      setStatus(`Your turn (${playerColor})`);
      return;
    }

    // Try center columns first (better strategy)
    const centerCols = [3, 2, 4, 1, 5, 0, 6];
    for (const col of centerCols) {
      if (grid[0][col] === 0) {
        makeMove(col);
        const w = winnerAt(grid);
        if (w){ endGame(w === humanPlayer); return; }
        if (isFull()){ endGame(false); return; }
        turn = humanPlayer;
        const playerColor = turn === 1 ? "Red" : "Yellow";
        setStatus(`Your turn (${playerColor})`);
        return;
      }
    }
  }

  function findWinningMove(player) {
    for (let x = 0; x < COLS; x++) {
      // Check if column is not full
      if (grid[0][x] === 0) {
        // Find the lowest empty row in this column
        let y = -1;
        for (let row = ROWS-1; row >= 0; row--) {
          if (grid[row][x] === 0) {
            y = row;
            break;
          }
        }
        if (y !== -1) {
          // Temporarily place the piece
          grid[y][x] = player;
          // Check if this creates a win
          if (checkWinAt(y, x, player)) {
            grid[y][x] = 0; // Remove the temporary piece
            return x;
          }
          grid[y][x] = 0; // Remove the temporary piece
        }
      }
    }
    return -1;
  }

  function checkWinAt(y, x, player) {
    const dirs = [[1,0],[0,1],[1,1],[1,-1]];
    for (const [dx,dy] of dirs){
      let count = 1;
      count += countDirection(x, y, dx, dy, player);
      count += countDirection(x, y, -dx, -dy, player);
      if (count >= 4) return true;
    }
    return false;
  }

  function countDirection(x, y, dx, dy, player) {
    let count = 0;
    let cx = x + dx, cy = y + dy;
    while (cx >= 0 && cx < COLS && cy >= 0 && cy < ROWS && grid[cy][cx] === player) {
      count++;
      cx += dx;
      cy += dy;
    }
    return count;
  }

  function isFull(){ for (let y=0;y<ROWS;y++) for (let x=0;x<COLS;x++) if (!grid[y][x]) return false; return true; }

  async function endGame(won){
    over = true; disable();
    const playerColor = turn === 1 ? "Red" : "Yellow";
    let message;
    if (won === false) {
      message = "🤝 Draw.";
    } else if (modeSel.value === "cpu") {
      message = won ? "🏆 You win!" : "🤖 CPU wins!";
    } else {
      message = `🏆 Player ${turn} (${playerColor}) wins!`;
    }
    setStatus(message);
    // Report result based on actual win state
    await reportResult(!!won);
  }

  function winnerAt(board) {
    // Check for any winner on the board
    for (let y = 0; y < ROWS; y++) {
      for (let x = 0; x < COLS; x++) {
        const p = board[y][x];
        if (!p) continue;

        const dirs = [[1,0],[0,1],[1,1],[1,-1]];
        for (const [dx,dy] of dirs){
          let c=1;
          c+=countDir(x,y,dx,dy,p);
          c+=countDir(x,y,-dx,-dy,p);
          if (c>=4) return p;
        }
      }
    }
    return 0;
  }

  function countDir(x,y,dx,dy,p){
    let c=0,cx=x+dx,cy=y+dy;
    while (cx>=0&&cx<COLS&&cy>=0&&cy<ROWS&&grid[cy][cx]===p){ c++; cx+=dx; cy+=dy; }
    return c;
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      resetBtn.addEventListener("click", init);
      modeSel.addEventListener("change", init);
      colorChoiceSel.addEventListener("change", init);
      init();
    });
  } else {
    resetBtn.addEventListener("click", init);
    modeSel.addEventListener("change", init);
    colorChoiceSel.addEventListener("change", init);
    init();
  }
})();