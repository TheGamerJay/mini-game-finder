// Enhanced Connect 4 Game Logic with difficulty modes and game counter

(function(){
  const COLS = 7, ROWS = 6;

  // DOM Elements - will be initialized in init()
  let boardEl, statusEl, resetBtn, startBtn, modeSel, colorChoiceSel, difficultyChoiceSel, gameCounterEl;

  let grid, turn, over, started, humanPlayer, cpuPlayer, difficulty;
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
    const { connect4_free_remaining = 0, credits = 0 } = gameCounter;
    gameCounterEl.textContent = `${5 - connect4_free_remaining}/5 free Connect 4 games used • ${credits} credits`;
  }

  async function beginRound(){
    try{
      const r = await fetch("/game/api/start", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ game: "connect4" })
      });
      const d = await r.json();
      if (!d.ok){
        if (d.error === "insufficient_credits"){
          setStatus(`Out of credits for extra plays. Need 5 credits.`);
        } else {
          setStatus("Unable to start. Please reload.");
        }
        disable();
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
      disable();
      return false;
    }
  }

  function setStatus(t){ statusEl.textContent = t; }
  function disable(){ boardEl.querySelectorAll(".c4-col").forEach(c=>c.classList.add("disabled")); }
  function enable(){ boardEl.querySelectorAll(".c4-col").forEach(c=>c.classList.remove("disabled")); }

  async function reportResult(won){
    try{
      await fetch("/game/api/result", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ game:"connect4", won: !!won })
      });
    } catch(e) {}
  }

  function canStartGame() {
    const hasMode = modeSel.value;
    const hasColor = colorChoiceSel.value;
    const hasDifficulty = modeSel.value === "pvp" || difficultyChoiceSel.value;

    return hasMode && hasColor && hasDifficulty;
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
    humanPlayer = parseInt(colorChoiceSel.value);
    cpuPlayer = humanPlayer === 1 ? 2 : 1;
    difficulty = difficultyChoiceSel.value || "easy";

    grid = Array(ROWS).fill().map(() => Array(COLS).fill(0));
    turn = 1; // Red always goes first
    over = false;
    started = false;

    // Create board
    createBoard();

    setStatus("Starting round…");
    const ok = await beginRound();
    if (!ok) return;

    // Show reset button, hide start button
    startBtn.style.display = "none";
    resetBtn.style.display = "inline-flex";

    // Disable form controls during game
    modeSel.disabled = true;
    colorChoiceSel.disabled = true;
    difficultyChoiceSel.disabled = true;

    if (modeSel.value === "cpu") {
      setStatus(turn === humanPlayer ? "Your turn" : "CPU's turn");
      if (turn === cpuPlayer) {
        setTimeout(aiMove, 500);
      }
    } else {
      const color = turn === 1 ? "Red" : "Yellow";
      setStatus(`${color} player's turn`);
    }
  }

  function resetGame() {
    // Re-enable form controls
    modeSel.disabled = false;
    colorChoiceSel.disabled = false;
    difficultyChoiceSel.disabled = false;

    // Show start button, hide reset button
    startBtn.style.display = "inline-flex";
    resetBtn.style.display = "none";

    // Clear board
    boardEl.innerHTML = "";

    // Reset game state
    grid = null;
    turn = null;
    over = false;
    started = false;

    setStatus("Please select difficulty and color to start playing");
    updateStartButton();
  }

  function createBoard(){
    boardEl.innerHTML = "";
    for (let col = 0; col < COLS; col++) {
      const colEl = document.createElement("div");
      colEl.className = "c4-col";
      colEl.dataset.col = col;
      colEl.addEventListener("click", () => onColumnClick(col));

      for (let row = 0; row < ROWS; row++) {
        const slot = document.createElement("div");
        slot.className = "c4-slot";
        slot.dataset.row = row;
        slot.dataset.col = col;
        colEl.appendChild(slot);
      }
      boardEl.appendChild(colEl);
    }
  }

  function onColumnClick(col){
    if (over || !started) return;

    // In CPU mode, only allow human moves
    if (modeSel.value === "cpu" && turn !== humanPlayer) return;

    if (dropPiece(col, turn)) {
      const winner = checkWin();
      if (winner) {
        endGame(winner);
        return;
      }
      if (isBoardFull()) {
        endGame(0); // Draw
        return;
      }

      turn = turn === 1 ? 2 : 1;

      if (modeSel.value === "cpu") {
        setStatus(turn === humanPlayer ? "Your turn" : "CPU's turn");
        if (turn === cpuPlayer) {
          setTimeout(aiMove, 500);
        }
      } else {
        const color = turn === 1 ? "Red" : "Yellow";
        setStatus(`${color} player's turn`);
      }
    }
  }

  function dropPiece(col, player) {
    for (let row = ROWS - 1; row >= 0; row--) {
      if (grid[row][col] === 0) {
        grid[row][col] = player;
        updateSlot(row, col, player);
        return true;
      }
    }
    return false; // Column full
  }

  function updateSlot(row, col, player) {
    const slot = boardEl.querySelector(`[data-row="${row}"][data-col="${col}"]`);
    if (slot) {
      slot.dataset.player = player;
    }
  }

  function aiMove(){
    if (over || !started) return;

    let col;

    // AI difficulty logic
    if (difficulty === "easy") {
      // Easy: Random moves most of the time, occasionally smart
      if (Math.random() < 0.8) {
        col = getRandomMove();
      } else {
        col = getBestMove(cpuPlayer) ?? getBestMove(humanPlayer) ?? getRandomMove();
      }
    } else if (difficulty === "medium") {
      // Medium: Smart defensive play, moderate offense
      if (Math.random() < 0.5) {
        col = getBestMove(cpuPlayer); // Try to win
      }
      if (col === null) {
        col = getBestMove(humanPlayer); // Block player
      }
      if (col === null) {
        col = getCenterBiasedMove();
      }
    } else { // hard
      // Hard: Always look for best move
      col = getBestMove(cpuPlayer) ?? getBestMove(humanPlayer) ?? getCenterBiasedMove() ?? getRandomMove();
    }

    if (col === null) {
      col = getRandomMove();
    }

    if (col !== null && dropPiece(col, cpuPlayer)) {
      const winner = checkWin();
      if (winner) {
        endGame(winner);
        return;
      }
      if (isBoardFull()) {
        endGame(0); // Draw
        return;
      }

      turn = humanPlayer;
      setStatus("Your turn");
    }
  }

  function getRandomMove() {
    const availableCols = [];
    for (let col = 0; col < COLS; col++) {
      if (grid[0][col] === 0) {
        availableCols.push(col);
      }
    }
    return availableCols.length > 0 ? availableCols[Math.floor(Math.random() * availableCols.length)] : null;
  }

  function getCenterBiasedMove() {
    // Prefer center columns
    const centerCols = [3, 2, 4, 1, 5, 0, 6];
    for (const col of centerCols) {
      if (grid[0][col] === 0) {
        return col;
      }
    }
    return null;
  }

  function getBestMove(player) {
    // Look for winning move or blocking move
    for (let col = 0; col < COLS; col++) {
      if (grid[0][col] === 0) {
        // Simulate the move
        const row = getDropRow(col);
        if (row !== -1) {
          grid[row][col] = player;
          if (checkWinFromPosition(row, col, player)) {
            grid[row][col] = 0; // Undo
            return col;
          }
          grid[row][col] = 0; // Undo
        }
      }
    }
    return null;
  }

  function getDropRow(col) {
    for (let row = ROWS - 1; row >= 0; row--) {
      if (grid[row][col] === 0) {
        return row;
      }
    }
    return -1; // Column full
  }

  function checkWin() {
    for (let row = 0; row < ROWS; row++) {
      for (let col = 0; col < COLS; col++) {
        const player = grid[row][col];
        if (player !== 0 && checkWinFromPosition(row, col, player)) {
          return player;
        }
      }
    }
    return 0;
  }

  function checkWinFromPosition(row, col, player) {
    const directions = [
      [0, 1],  // horizontal
      [1, 0],  // vertical
      [1, 1],  // diagonal \
      [1, -1]  // diagonal /
    ];

    for (const [dr, dc] of directions) {
      let count = 1;

      // Check positive direction
      for (let i = 1; i < 4; i++) {
        const r = row + dr * i;
        const c = col + dc * i;
        if (r >= 0 && r < ROWS && c >= 0 && c < COLS && grid[r][c] === player) {
          count++;
        } else {
          break;
        }
      }

      // Check negative direction
      for (let i = 1; i < 4; i++) {
        const r = row - dr * i;
        const c = col - dc * i;
        if (r >= 0 && r < ROWS && c >= 0 && c < COLS && grid[r][c] === player) {
          count++;
        } else {
          break;
        }
      }

      if (count >= 4) {
        return true;
      }
    }
    return false;
  }

  function isBoardFull() {
    return grid[0].every(cell => cell !== 0);
  }

  async function endGame(winner){
    over = true;
    disable();

    let message, won;

    if (winner === 0) {
      message = "🤝 Draw!";
      won = false;
    } else if (modeSel.value === "cpu") {
      won = winner === humanPlayer;
      const color = winner === 1 ? "Red" : "Yellow";
      message = won ? `🏆 You win with ${color}!` : `🤖 CPU wins with ${color}!`;
    } else {
      const color = winner === 1 ? "Red" : "Yellow";
      message = `🏆 ${color} player wins!`;
      won = winner === 1; // Red is considered player 1
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
        difficultyChoiceSel.style.display = "none";
        if (difficultyChoiceSel.previousElementSibling) {
          difficultyChoiceSel.previousElementSibling.style.display = "none";
        }
      } else {
        difficultyChoiceSel.style.display = "inline";
        if (difficultyChoiceSel.previousElementSibling) {
          difficultyChoiceSel.previousElementSibling.style.display = "inline";
        }
      }
      updateStartButton();
    });

    colorChoiceSel.addEventListener("change", updateStartButton);
    difficultyChoiceSel.addEventListener("change", updateStartButton);
  }

  // Initialize when DOM is ready
  function init() {
    // Initialize DOM elements
    boardEl = document.getElementById("c4Board");
    statusEl = document.getElementById("c4Status");
    resetBtn = document.getElementById("c4Reset");
    startBtn = document.getElementById("c4Start");
    modeSel = document.getElementById("c4Mode");
    colorChoiceSel = document.getElementById("colorChoice");
    difficultyChoiceSel = document.getElementById("difficultyChoice");
    gameCounterEl = document.getElementById("gameCounterDisplay");

    setupEventListeners();
    loadGameCounter();
    updateStartButton();

    // Initially hide difficulty for PvP mode
    if (modeSel.value === "pvp") {
      difficultyChoiceSel.style.display = "none";
      if (difficultyChoiceSel.previousElementSibling) {
        difficultyChoiceSel.previousElementSibling.style.display = "none";
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();