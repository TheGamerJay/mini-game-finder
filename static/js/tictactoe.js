// Tic-tac-toe Game Logic - moved from inline script for CSP compliance

(function(){
  const boardEl = document.getElementById("tttBoard");
  const statusEl = document.getElementById("tttStatus");
  const resetBtn = document.getElementById("tttReset");
  const modeSel  = document.getElementById("tttMode");
  const playerChoiceSel = document.getElementById("playerChoice");
  const playerChoiceLabel = document.getElementById("playerChoiceLabel");

  const X = "X", O = "O";
  let board, turn, over, started, humanSymbol, cpuSymbol;

  async function beginRound(){
    try{
      const r = await fetch("/game/api/start", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ game: "ttt" })
      });
      const d = await r.json();
      if (!d.ok){
        if (d.error === "insufficient_credits"){
          setStatus(`Out of credits for extra plays. Need ${5} credits.`);
        } else {
          setStatus("Unable to start. Please reload.");
        }
        disableBoard(); return false;
      }
      const note = d.charged ? `-${d.charged} credits` : `free`;
      setStatus(`Round started (${note}). Free plays left: ${d.free_remaining}. Credits: ${d.credits}.`);
      started = true; return true;
    }catch{ setStatus("Network error."); disableBoard(); return false; }
  }

  function setStatus(t){ statusEl.textContent = t; }
  function disableBoard(){ boardEl.querySelectorAll(".ttt-cell").forEach(c=>c.classList.add("disabled")); }

  async function reportResult(win){
    try{ await fetch("/game/api/result", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ game:"ttt", won: !!win })
    }); }catch{}
  }

  async function init(){
    // Show/hide player choice based on mode
    if (modeSel.value === "cpu") {
      playerChoiceLabel.style.display = "inline-block";
      humanSymbol = playerChoiceSel.value;
      cpuSymbol = humanSymbol === X ? O : X;
    } else {
      playerChoiceLabel.style.display = "none";
      humanSymbol = X;
      cpuSymbol = O;
    }

    board = Array(9).fill(null); turn = X; over = false; started = false;
    boardEl.innerHTML = "";
    for (let i=0;i<9;i++){
      const cell = document.createElement("button");
      cell.className = "ttt-cell"; cell.dataset.idx = i;
      cell.addEventListener("click", onCell);
      boardEl.appendChild(cell);
    }
    setStatus("Starting round…");
    const ok = await beginRound(); if (!ok) return;

    if (modeSel.value === "cpu") {
      setStatus(turn === humanSymbol ? "Your turn" : "CPU's turn");
      if (turn === cpuSymbol) setTimeout(aiMove, 250);
    } else {
      setStatus(`${turn}'s turn`);
    }
  }

  function onCell(e){
    if (over || !started) return;
    // In CPU mode, only allow human moves
    if (modeSel.value === "cpu" && turn !== humanSymbol) return;

    const idx = Number(e.currentTarget.dataset.idx);
    if (board[idx]) return;
    move(idx, turn);
    const winner = getWinner(board);
    if (winner || isFull(board)) { endGame(winner); return; }
    turn = (turn===X)?O:X;

    if (modeSel.value === "cpu") {
      setStatus(turn === humanSymbol ? "Your turn" : "CPU's turn");
      if (turn === cpuSymbol) setTimeout(aiMove, 250);
    } else {
      setStatus(`${turn}'s turn`);
    }
  }

  function move(idx, sym){
    board[idx] = sym;
    const cell = boardEl.querySelector(`[data-idx="${idx}"]`);
    if (cell){ cell.textContent = sym; cell.classList.add("disabled"); }
  }

  function aiMove(){
    if (over || !started) return;
    let idx = bestMove(cpuSymbol) ?? bestMove(humanSymbol) ?? (board[4] ? null : 4);
    if (idx == null){
      const empties = board.map((v,i)=>v?null:i).filter(v=>v!=null);
      idx = empties[Math.floor(Math.random()*empties.length)];
    }
    move(idx, cpuSymbol);
    const winner = getWinner(board);
    if (winner || isFull(board)) { endGame(winner); return; }
    turn = humanSymbol;
    setStatus("Your turn");
  }

  function bestMove(sym){
    for (let i=0;i<9;i++){
      if (!board[i]){
        board[i]=sym;
        if (getWinner(board)===sym){ board[i]=null; return i; }
        board[i]=null;
      }
    } return null;
  }

  function getWinner(b){
    const L=[[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
    for (const [a,c,d] of L){ if (b[a] && b[a]===b[c] && b[a]===b[d]) return b[a]; }
    return null;
  }
  const isFull = b => b.every(Boolean);

  async function endGame(winner){
    over = true; disableBoard();
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

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      resetBtn.addEventListener("click", init);
      modeSel.addEventListener("change", init);
      playerChoiceSel.addEventListener("change", init);
      init();
    });
  } else {
    resetBtn.addEventListener("click", init);
    modeSel.addEventListener("change", init);
    playerChoiceSel.addEventListener("change", init);
    init();
  }
})();