// Enhanced Connect 4 Game Logic - Professional Architecture Implementation

(function(){
  'use strict';

  // Game constants
  const COLS = 7, ROWS = 6;
  const GAME_NAME = 'c4';

  // Game state
  let grid, turn, over, started, humanPlayer, cpuPlayer, difficulty;
  let gameCounter = { free_remaining: 0, credits: 0 };
  let lifecycle;

  // DOM Elements - initialized in init()
  let elements = {};
  let logger = window.Logger.createLogger('CONNECT-4');
  let gameAPI = window.HTTP.createHTTPClient('/game/api', {
    validate: window.HTTP.createValidator({ ok: 'boolean' })
  });

  // Required element IDs for this game
  const REQUIRED_ELEMENTS = [
    'c4Board', 'c4Status', 'c4Reset', 'c4Start', 'c4Mode',
    'colorChoice', 'difficultyChoice', 'credits-display'
  ];

  // Load game counter using SWR cache
  async function loadGameCounter() {
    try {
      const data = await window.SWR.swr(
        'game-status',
        () => gameAPI.get('/status'),
        { ttl: 30000, staleTime: 10000 }
      );

      if (data.ok) {
        gameCounter = data;
        updateCounterDisplay();
        logger.debug('Game counter loaded:', data);
      }
    } catch (e) {
      logger.warn('Could not load game counter:', e.message);
    }
  }

  function updateCounterDisplay() {
    const { connect4_free_remaining = 5, credits = 0 } = gameCounter;
    const used = 5 - connect4_free_remaining;
    elements.creditsDisplay.textContent = credits.toLocaleString();
  }

  async function beginRound(){
    try{
      const d = await gameAPI.post('/start', { game: GAME_NAME });

      if (!d.ok){
        if (d.error === "insufficient_credits"){
          setStatus(`Out of credits for extra plays. Need 5 credits.`);
        } else {
          setStatus("Unable to start. Please reload.");
        }
        disable();
        return false;
      }

      // Update game counter and cache
      gameCounter = d;
      updateCounterDisplay();
      window.SWR.mutate('game-status', d);

      const note = d.charged ? `-${d.charged} credits` : `free`;
      setStatus(`Round started (${note}). Free plays left: ${d.free_remaining || 0}.`);
      started = true;

      logger.info('Round started:', { charged: d.charged, remaining: d.free_remaining });
      window.Bus.emit('game:started', { game: GAME_NAME, data: d });

      return true;
    } catch(e) {
      logger.error('Begin round failed:', e);
      setStatus("Network error.");
      disable();
      return false;
    }
  }

  function setStatus(t){ elements.c4Status.textContent = t; }
  function disable(){ elements.c4Board.querySelectorAll(".c4-col").forEach(c=>c.classList.add("disabled")); }

  async function reportResult(won){
    try{
      await gameAPI.post('/result', { game: GAME_NAME, won: !!won });
      logger.info('Game result reported:', { won: !!won });
      window.Bus.emit('game:ended', { game: GAME_NAME, won: !!won });

      // Invalidate game status cache to refresh counters
      window.SWR.invalidate('game-status');
    } catch(e) {
      logger.warn('Failed to report result:', e.message);
    }
  }

  function canStartGame() {
    const hasMode = elements.c4Mode.value;
    const hasColor = elements.colorChoice.value;
    const hasDifficulty = elements.c4Mode.value === "pvp" || elements.difficultyChoice.value;

    return hasMode && hasColor && hasDifficulty;
  }

  function updateStartButton() {
    elements.c4Start.disabled = !canStartGame();
    if (canStartGame()) {
      elements.c4Start.textContent = "Start Game";
      elements.c4Start.style.opacity = "1";
    } else {
      elements.c4Start.textContent = "Select Options First";
      elements.c4Start.style.opacity = "0.6";
    }
  }

  const startGame = window.NavGuard.guardedClick(async function(){
    if (!canStartGame()) {
      setStatus("Please select all options first");
      return;
    }

    logger.info('Starting game with settings:', {
      mode: elements.c4Mode.value,
      color: elements.colorChoice.value,
      difficulty: elements.difficultyChoice.value
    });

    // Set up game variables
    humanPlayer = parseInt(elements.colorChoice.value);
    cpuPlayer = humanPlayer === 1 ? 2 : 1;
    difficulty = elements.difficultyChoice.value || "easy";

    grid = Array(ROWS).fill().map(() => Array(COLS).fill(0));
    turn = 1; // Red always goes first
    over = false;
    started = false;

    // Create board with performance optimization
    createBoard();

    setStatus("Starting round…");
    const ok = await beginRound();
    if (!ok) return;

    // Show reset button, hide start button
    elements.c4Start.style.display = "none";
    elements.c4Reset.style.display = "inline-flex";

    // Disable form controls during game
    elements.c4Mode.disabled = true;
    elements.colorChoice.disabled = true;
    elements.difficultyChoice.disabled = true;

    if (elements.c4Mode.value === "cpu") {
      setStatus(turn === humanPlayer ? "Your turn" : "CPU's turn");
      if (turn === cpuPlayer) {
        window.Scheduler.afterFrame(() => aiMove());
      }
    } else {
      const color = turn === 1 ? "Red" : "Yellow";
      setStatus(`${color} player's turn`);
    }
  }, { key: 'c4-start-game' });

  function resetGame() {
    // Re-enable form controls
    elements.c4Mode.disabled = false;
    elements.colorChoice.disabled = false;
    elements.difficultyChoice.disabled = false;

    // Show start button, hide reset button
    elements.c4Start.style.display = "inline-flex";
    elements.c4Reset.style.display = "none";

    // Clear board
    elements.c4Board.innerHTML = "";

    // Reset game state
    grid = null;
    turn = null;
    over = false;
    started = false;

    setStatus("Please select difficulty and color to start playing");
    updateStartButton();
  }

  function createBoard(){
    window.DOMBatch.batchWrites(() => {
      elements.c4Board.innerHTML = "";
      elements.c4Board.classList.add('animating');

      for (let col = 0; col < COLS; col++) {
        const colEl = document.createElement("div");
        colEl.className = "c4-col";
        colEl.dataset.col = col;

        for (let row = 0; row < ROWS; row++) {
          const slot = document.createElement("div");
          slot.className = "c4-slot";
          slot.dataset.row = row;
          slot.dataset.col = col;
          colEl.appendChild(slot);
        }
        elements.c4Board.appendChild(colEl);
      }
    });

    // Use delegation for column clicks instead of individual listeners
    window.DOMBatch.afterRender(() => {
      window.Delegate.delegate(elements.c4Board, 'click', '.c4-col', (e, target) => {
        const col = parseInt(target.dataset.col);
        onColumnClick(col);
      });

      elements.c4Board.classList.remove('animating');
      logger.debug('Board created with delegation');
    });
  }

  function onColumnClick(col){
    if (over || !started) return;

    // In CPU mode, only allow human moves
    if (elements.c4Mode.value === "cpu" && turn !== humanPlayer) return;

    logger.debug('Column clicked:', { col, turn });

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

      if (elements.c4Mode.value === "cpu") {
        setStatus(turn === humanPlayer ? "Your turn" : "CPU's turn");
        if (turn === cpuPlayer) {
          window.Scheduler.afterFrame(() => aiMove());
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
    const slot = elements.c4Board.querySelector(`[data-row="${row}"][data-col="${col}"]`);
    if (slot) {
      window.DOMBatch.batchWrites(() => {
        slot.dataset.player = player;
        window.Query.setState(slot, 'player', player);
      });
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
    } else if (elements.c4Mode.value === "cpu") {
      won = winner === humanPlayer;
      const color = winner === 1 ? "Red" : "Yellow";
      message = won ? `🏆 You win with ${color}!` : `🤖 CPU wins with ${color}!`;
    } else {
      const color = winner === 1 ? "Red" : "Yellow";
      message = `🏆 ${color} player wins!`;
      won = winner === 1; // Red is considered player 1
    }

    logger.info('Game ended:', { winner, won, mode: elements.c4Mode.value });
    setStatus(message);

    // Report result with performance monitoring
    const perfLogger = window.Logger.createPerformanceLogger('CONNECT-4-API');
    await perfLogger.measureAsync(() => reportResult(won), 'Report Result');
  }

  // Event listeners setup
  function setupEventListeners() {
    elements.c4Reset.addEventListener("click", resetGame);
    elements.c4Start.addEventListener("click", startGame);

    // Update start button when selections change
    elements.c4Mode.addEventListener("change", function() {
      // Show/hide difficulty based on mode
      if (this.value === "pvp") {
        elements.difficultyChoice.style.display = "none";
        if (elements.difficultyChoice.previousElementSibling) {
          elements.difficultyChoice.previousElementSibling.style.display = "none";
        }
      } else {
        elements.difficultyChoice.style.display = "inline";
        if (elements.difficultyChoice.previousElementSibling) {
          elements.difficultyChoice.previousElementSibling.style.display = "inline";
        }
      }
      updateStartButton();
    });

    elements.colorChoice.addEventListener("change", updateStartButton);
    elements.difficultyChoice.addEventListener("change", updateStartButton);
  }

  // Professional initialization with bulletproof DOM-ready and lifecycle management
  function init() {
    // Create lifecycle manager for cleanup
    lifecycle = window.Lifecycles.createLifecycle();

    // Get all required elements using professional DOM-ready utilities
    const elementsMap = window.DOMReady.getRequiredElements(REQUIRED_ELEMENTS, 'Connect 4 Game');

    if (!elementsMap) {
      logger.error('Failed to initialize - missing required elements');
      return;
    }

    // Map elements for easy access
    elements = {
      c4Board: elementsMap.c4Board,
      c4Status: elementsMap.c4Status,
      c4Reset: elementsMap.c4Reset,
      c4Start: elementsMap.c4Start,
      c4Mode: elementsMap.c4Mode,
      colorChoice: elementsMap.colorChoice,
      difficultyChoice: elementsMap.difficultyChoice,
      creditsDisplay: elementsMap.creditsDisplay
    };

    logger.info('All elements found, initializing game...');

    // Add performance CSS classes
    elements.c4Board.classList.add('arcade-game-container', 'game-board');

    setupEventListeners();
    loadGameCounter();
    updateStartButton();

    // Initially hide difficulty for PvP mode
    if (elements.c4Mode.value === "pvp") {
      elements.difficultyChoice.style.display = "none";
      if (elements.difficultyChoice.previousElementSibling) {
        elements.difficultyChoice.previousElementSibling.style.display = "none";
      }
    }

    // Subscribe to global game events
    lifecycle.addCleanup(
      window.Bus.on('game:reload-counters', loadGameCounter)
    );

    logger.info('Game initialized successfully');
  }

  // Use bulletproof DOM-ready pattern with init guard
  const initOnce = window.DOMReady.createInitOnce();
  window.DOMReady.onDomReady(() => initOnce(init));

})();