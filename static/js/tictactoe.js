// Enhanced Tic-tac-toe Game Logic - Professional Architecture Implementation

(function(){
  'use strict';

  // Game constants
  const X = "X", O = "O";
  const GAME_NAME = 'ttt';

  // Game state
  let board, turn, over, started, humanSymbol, cpuSymbol, difficulty;
  let gameCounter = { free_remaining: 0, credits: 0 };
  let lifecycle;

  // DOM Elements - initialized in init()
  let elements = {};
  let logger = window.Logger.createLogger('TIC-TAC-TOE');
  let gameAPI = window.HTTP.createHTTPClient('/game/api', {
    validate: window.HTTP.createValidator({ ok: 'boolean' })
  });

  // Required element IDs for this game
  const REQUIRED_ELEMENTS = [
    'tttBoard', 'tttStatus', 'tttReset', 'tttStart', 'tttMode',
    'playerChoice', 'difficultyChoice', 'gameCounterDisplay'
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
    const { tictactoe_free_remaining = 0, credits = 0 } = gameCounter;
    elements.gameCounterDisplay.textContent = `${5 - tictactoe_free_remaining}/5 free Tic-Tac-Toe games used • ${credits} credits`;
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
        disableBoard();
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
      disableBoard();
      return false;
    }
  }

  function setStatus(t){ elements.tttStatus.textContent = t; }
  function disableBoard(){ elements.tttBoard.querySelectorAll(".ttt-cell").forEach(c=>c.classList.add("disabled")); }

  async function reportResult(win){
    try{
      await gameAPI.post('/result', { game: GAME_NAME, won: !!win });
      logger.info('Game result reported:', { won: !!win });
      window.Bus.emit('game:ended', { game: GAME_NAME, won: !!win });

      // Invalidate game status cache to refresh counters
      window.SWR.invalidate('game-status');
    } catch(e) {
      logger.warn('Failed to report result:', e.message);
    }
  }

  function canStartGame() {
    const hasMode = elements.tttMode.value;
    const hasSymbol = elements.playerChoice.value;
    const hasDifficulty = elements.tttMode.value === "pvp" || elements.difficultyChoice.value;

    return hasMode && hasSymbol && hasDifficulty;
  }

  function updateStartButton() {
    elements.tttStart.disabled = !canStartGame();
    if (canStartGame()) {
      elements.tttStart.textContent = "Start Game";
      elements.tttStart.style.opacity = "1";
    } else {
      elements.tttStart.textContent = "Select Options First";
      elements.tttStart.style.opacity = "0.6";
    }
  }

  const startGame = window.NavGuard.guardedClick(async function(){
    if (!canStartGame()) {
      setStatus("Please select all options first");
      return;
    }

    logger.info('Starting game with settings:', {
      mode: elements.tttMode.value,
      symbol: elements.playerChoice.value,
      difficulty: elements.difficultyChoice.value
    });

    // Set up game variables
    humanSymbol = elements.playerChoice.value;
    cpuSymbol = humanSymbol === X ? O : X;
    difficulty = elements.difficultyChoice.value || "easy";

    board = Array(9).fill(null);
    turn = X;
    over = false;
    started = false;

    // Clear and create board using DOM batching
    window.DOMBatch.batchWrites(() => {
      elements.tttBoard.innerHTML = "";
      for (let i=0; i<9; i++){
        const cell = document.createElement("button");
        cell.className = "ttt-cell";
        cell.dataset.idx = i;
        elements.tttBoard.appendChild(cell);
      }
    });

    // Use delegation for cell clicks instead of individual listeners
    window.DOMBatch.afterRender(() => {
      window.Delegate.delegate(elements.tttBoard, 'click', '.ttt-cell', onCell);
    });

    setStatus("Starting round…");
    const ok = await beginRound();
    if (!ok) return;

    // Show reset button, hide start button
    elements.tttStart.style.display = "none";
    elements.tttReset.style.display = "inline-flex";

    // Disable form controls during game
    elements.tttMode.disabled = true;
    elements.playerChoice.disabled = true;
    elements.difficultyChoice.disabled = true;

    if (elements.tttMode.value === "cpu") {
      setStatus(turn === humanSymbol ? "Your turn" : "CPU's turn");
      if (turn === cpuSymbol) {
        window.Scheduler.afterFrame(() => aiMove());
      }
    } else {
      setStatus(`${turn}'s turn`);
    }
  }, { key: 'ttt-start-game' });

  function resetGame() {
    // Re-enable form controls
    elements.tttMode.disabled = false;
    elements.playerChoice.disabled = false;
    elements.difficultyChoice.disabled = false;

    // Show start button, hide reset button
    elements.tttStart.style.display = "inline-flex";
    elements.tttReset.style.display = "none";

    // Clear board
    elements.tttBoard.innerHTML = "";

    // Reset game state
    board = null;
    turn = null;
    over = false;
    started = false;

    setStatus("Please select difficulty and symbol to start playing");
    updateStartButton();
  }

  function onCell(e, target){
    if (over || !started) return;

    // In CPU mode, only allow human moves
    if (elements.tttMode.value === "cpu" && turn !== humanSymbol) return;

    const idx = Number(target.dataset.idx);
    if (board[idx]) return;

    logger.debug('Cell clicked:', { idx, turn });

    move(idx, turn);
    const winner = getWinner(board);
    if (winner || isFull(board)) {
      endGame(winner);
      return;
    }

    turn = (turn===X) ? O : X;

    if (elements.tttMode.value === "cpu") {
      setStatus(turn === humanSymbol ? "Your turn" : "CPU's turn");
      if (turn === cpuSymbol) {
        window.Scheduler.afterFrame(() => aiMove());
      }
    } else {
      setStatus(`${turn}'s turn`);
    }
  }

  function move(idx, sym){
    board[idx] = sym;
    const cell = window.Query.data('idx', idx, elements.tttBoard);
    if (cell){
      window.DOMBatch.batchWrites(() => {
        cell.textContent = sym;
        cell.classList.add("disabled");
        window.Query.setState(cell, 'player', sym);
      });
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
    } else if (elements.tttMode.value === "cpu") {
      won = winner === humanSymbol;
      message = won ? "🏆 You win!" : "🤖 CPU wins!";
    } else {
      won = winner === X; // In PvP, X is considered player 1
      message = `🏆 ${winner} wins!`;
    }

    logger.info('Game ended:', { winner, won, mode: elements.tttMode.value });
    setStatus(message);

    // Report result with performance monitoring
    const perfLogger = window.Logger.createPerformanceLogger('TIC-TAC-TOE-API');
    await perfLogger.measureAsync(() => reportResult(won), 'Report Result');
  }

  // Event listeners setup
  function setupEventListeners() {
    elements.tttReset.addEventListener("click", resetGame);
    elements.tttStart.addEventListener("click", startGame);

    // Update start button when selections change
    elements.tttMode.addEventListener("change", function() {
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

    elements.playerChoice.addEventListener("change", updateStartButton);
    elements.difficultyChoice.addEventListener("change", updateStartButton);
  }

  // Professional initialization with bulletproof DOM-ready and lifecycle management
  function init() {
    // Create lifecycle manager for cleanup
    lifecycle = window.Lifecycles.createLifecycle();

    // Get all required elements using professional DOM-ready utilities
    const elementsMap = window.DOMReady.getRequiredElements(REQUIRED_ELEMENTS, 'Tic-Tac-Toe Game');

    if (!elementsMap) {
      logger.error('Failed to initialize - missing required elements');
      return;
    }

    // Map elements for easy access
    elements = {
      tttBoard: elementsMap.tttBoard,
      tttStatus: elementsMap.tttStatus,
      tttReset: elementsMap.tttReset,
      tttStart: elementsMap.tttStart,
      tttMode: elementsMap.tttMode,
      playerChoice: elementsMap.playerChoice,
      difficultyChoice: elementsMap.difficultyChoice,
      gameCounterDisplay: elementsMap.gameCounterDisplay
    };

    logger.info('All elements found, initializing game...');

    // Add performance CSS classes
    elements.tttBoard.classList.add('arcade-game-container', 'game-board');

    setupEventListeners();
    loadGameCounter();
    updateStartButton();

    // Initially hide difficulty for PvP mode
    if (elements.tttMode.value === "pvp") {
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