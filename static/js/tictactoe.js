// Enhanced Tic-tac-toe Game Logic with difficulty modes and game counter

(function(){
  const boardEl = document.getElementById("tttBoard");
  const statusEl = document.getElementById("tttStatus");
  const resetBtn = document.getElementById("tttReset");
  const startBtn = document.getElementById("tttStart");
  const modeSel = document.getElementById("tttMode");
  const playerChoiceSel = document.getElementById("playerChoice");
  const difficultyChoiceSel = document.getElementById("difficultyChoice");
  const gameCounterEl = document.getElementById("gameCounterDisplay");

  const X = "X", O = "O";
  let board, turn, over, started, humanSymbol, cpuSymbol, difficulty;
  let gameCounter = { free_remaining: 0, credits: 0 };

  // Load game counter on page load
  async function loadGameCounter() {
    try {
      const response = await fetch("/game/api/status", {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      });
      const data = await response.json();
      if (data.ok) {
        gameCounter = data;
        updateCounterDisplay();
      }
    } catch (e) {
      console.log("Could not load game counter");
    }
  }

  function updateCounterDisplay() {
    const { tictactoe_free_remaining = 0, credits = 0 } = gameCounter;
    gameCounterEl.textContent = `${5 - tictactoe_free_remaining}/5 free Tic-Tac-Toe games used • ${credits} credits`;
  }

  async function beginRound(){
    try{
      const r = await fetch("/game/api/start", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ game: "tictactoe" })
      });
      const d = await r.json();
      if (!d.ok){
        if (d.error === "insufficient_credits"){
          setStatus(`Out of credits for extra plays. Need 5 credits.`);
        } else {
          setStatus("Unable to start. Please reload.");
        }
        disableBoard();
        return false;
      }

      // Update game counter
      gameCounter = d;
      updateCounterDisplay();

      const note = d.charged ? `-${d.charged} credits` : `free`;
      setStatus(`Round started (${note}). Free plays left: ${d.free_remaining || 0}.`);
      started = true;
      return true;
    } catch(e) {
      setStatus("Network error.");
      disableBoard();
      return false;
    }
  }

  function setStatus(t){ statusEl.textContent = t; }
  function disableBoard(){ boardEl.querySelectorAll(".ttt-cell").forEach(c=>c.classList.add("disabled")); }
  function enableBoard(){ boardEl.querySelectorAll(".ttt-cell").forEach(c=>c.classList.remove("disabled")); }

  async function reportResult(win){
    try{
      await fetch("/game/api/result", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ game:"tictactoe", won: !!win })
      });
    } catch(e) {}
  }

  function canStartGame() {
    const hasMode = modeSel.value;
    const hasSymbol = playerChoiceSel.value;
    const hasDifficulty = modeSel.value === "pvp" || difficultyChoiceSel.value;

    return hasMode && hasSymbol && hasDifficulty;
  }

  function updateStartButton() {
    startBtn.disabled = !canStartGame();
    if (canStartGame()) {
      startBtn.textContent = "Start Game";
      startBtn.style.opacity = "1";
    } else {
      startBtn.textContent = "Select Options First";
      startBtn.style.opacity = "0.6";
    }
  }

  async function startGame(){
    if (!canStartGame()) {
      setStatus("Please select all options first");
      return;
    }

    // Set up game variables
    humanSymbol = playerChoiceSel.value;
    cpuSymbol = humanSymbol === X ? O : X;
    difficulty = difficultyChoiceSel.value || "easy";

    board = Array(9).fill(null);
    turn = X;
    over = false;
    started = false;

    // Clear and create board
    boardEl.innerHTML = "";
    for (let i=0; i<9; i++){
      const cell = document.createElement("button");
      cell.className = "ttt-cell";
      cell.dataset.idx = i;
      cell.addEventListener("click", onCell);
      boardEl.appendChild(cell);
    }

    setStatus("Starting round…");
    const ok = await beginRound();
    if (!ok) return;

    // Show reset button, hide start button
    startBtn.style.display = "none";
    resetBtn.style.display = "inline-flex";

    // Disable form controls during game
    modeSel.disabled = true;
    playerChoiceSel.disabled = true;
    difficultyChoiceSel.disabled = true;

    if (modeSel.value === "cpu") {
      setStatus(turn === humanSymbol ? "Your turn" : "CPU's turn");
      if (turn === cpuSymbol) {
        setTimeout(aiMove, 250);
      }
    } else {
      setStatus(`${turn}'s turn`);
    }
  }

  function resetGame() {
    // Re-enable form controls
    modeSel.disabled = false;
    playerChoiceSel.disabled = false;
    difficultyChoiceSel.disabled = false;

    // Show start button, hide reset button
    startBtn.style.display = "inline-flex";
    resetBtn.style.display = "none";

    // Clear board
    boardEl.innerHTML = "";

    // Reset game state
    board = null;
    turn = null;
    over = false;
    started = false;

    setStatus("Please select difficulty and symbol to start playing");
    updateStartButton();
  }

  function onCell(e){
    if (over || !started) return;

    // In CPU mode, only allow human moves
    if (modeSel.value === "cpu" && turn !== humanSymbol) return;

    const idx = Number(e.currentTarget.dataset.idx);
    if (board[idx]) return;

    move(idx, turn);
    const winner = getWinner(board);
    if (winner || isFull(board)) {
      endGame(winner);
      return;
    }

    turn = (turn===X) ? O : X;

    if (modeSel.value === "cpu") {
      setStatus(turn === humanSymbol ? "Your turn" : "CPU's turn");
      if (turn === cpuSymbol) {
        setTimeout(aiMove, 250);
      }
    } else {
      setStatus(`${turn}'s turn`);
    }
  }

  function move(idx, sym){
    board[idx] = sym;
    const cell = boardEl.querySelector(`[data-idx="${idx}"]`);
    if (cell){
      cell.textContent = sym;
      cell.classList.add("disabled");
    }
  }

  function aiMove(){
    if (over || !started) return;

    let idx;

    // AI difficulty logic
    if (difficulty === "easy") {
      // Easy: Random moves most of the time, occasionally smart
      if (Math.random() < 0.7) {
        idx = getRandomMove();
      } else {
        idx = bestMove(cpuSymbol) ?? bestMove(humanSymbol) ?? getRandomMove();
      }
    } else if (difficulty === "medium") {
      // Medium: Smart defensive play, but not always optimal offense
      if (Math.random() < 0.4) {
        idx = bestMove(cpuSymbol); // Try to win
      }
      if (idx == null) {
        idx = bestMove(humanSymbol); // Block player
      }
      if (idx == null) {
        idx = getRandomMove();
      }
    } else { // hard
      // Hard: Always optimal play
      idx = bestMove(cpuSymbol) ?? bestMove(humanSymbol) ?? getCenterOrCorner() ?? getRandomMove();
    }

    if (idx == null) {
      idx = getRandomMove();
    }

    move(idx, cpuSymbol);
    const winner = getWinner(board);
    if (winner || isFull(board)) {
      endGame(winner);
      return;
    }

    turn = humanSymbol;
    setStatus("Your turn");
  }

  function getRandomMove() {
    const empties = board.map((v,i)=>v?null:i).filter(v=>v!=null);
    return empties.length > 0 ? empties[Math.floor(Math.random()*empties.length)] : null;
  }

  function getCenterOrCorner() {
    // Prefer center, then corners
    if (!board[4]) return 4;
    const corners = [0, 2, 6, 8];
    const availableCorners = corners.filter(i => !board[i]);
    return availableCorners.length > 0 ? availableCorners[Math.floor(Math.random() * availableCorners.length)] : null;
  }

  function bestMove(sym){
    for (let i=0; i<9; i++){
      if (!board[i]){
        board[i] = sym;
        if (getWinner(board) === sym){
          board[i] = null;
          return i;
        }
        board[i] = null;
      }
    }
    return null;
  }

  function getWinner(b){
    const lines = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
    for (const [a,c,d] of lines){
      if (b[a] && b[a]===b[c] && b[a]===b[d]) return b[a];
    }
    return null;
  }

  const isFull = b => b.every(Boolean);

  async function endGame(winner){
    over = true;
    disableBoard();

    let message, won;

    if (!winner) {
      message = "🤝 Draw.";
      won = false;
    } else if (modeSel.value === "cpu") {
      won = winner === humanSymbol;
      message = won ? "🏆 You win!" : "🤖 CPU wins!";
    } else {
      won = winner === X; // In PvP, X is considered player 1
      message = `🏆 ${winner} wins!`;
    }

    setStatus(message);
    await reportResult(won);
  }

  // Event listeners
  function setupEventListeners() {
    resetBtn.addEventListener("click", resetGame);
    startBtn.addEventListener("click", startGame);

    // Update start button when selections change
    modeSel.addEventListener("change", function() {
      // Show/hide difficulty based on mode
      if (this.value === "pvp") {
        if (difficultyChoiceSel) {
          difficultyChoiceSel.style.display = "none";
          if (difficultyChoiceSel.previousElementSibling) {
            difficultyChoiceSel.previousElementSibling.style.display = "none";
          }
        }
      } else {
        if (difficultyChoiceSel) {
          difficultyChoiceSel.style.display = "inline";
          if (difficultyChoiceSel.previousElementSibling) {
            difficultyChoiceSel.previousElementSibling.style.display = "inline";
          }
        }
      }
      updateStartButton();
    });

    if (playerChoiceSel) {
      playerChoiceSel.addEventListener("change", updateStartButton);
    }
    if (difficultyChoiceSel) {
      difficultyChoiceSel.addEventListener("change", updateStartButton);
    }
  }

  // Initialize when DOM is ready
  function init() {
    setupEventListeners();
    loadGameCounter();
    updateStartButton();

    // Initially hide difficulty for PvP mode
    if (modeSel && modeSel.value === "pvp") {
      if (difficultyChoiceSel) {
        difficultyChoiceSel.style.display = "none";
        if (difficultyChoiceSel.previousElementSibling) {
          difficultyChoiceSel.previousElementSibling.style.display = "none";
        }
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();