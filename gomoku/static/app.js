const BOARD_SIZE = 15;
const STAR_POINTS = [
  [3, 3],
  [3, 11],
  [7, 7],
  [11, 3],
  [11, 11],
];
const COL_LABELS = Array.from({ length: BOARD_SIZE }, (_, index) => String.fromCharCode("A".charCodeAt(0) + index));
const state = {
  socket: null,
  roomId: new URLSearchParams(window.location.search).get("room") || "",
  playerId: localStorage.getItem("gomoku_player_id") || "",
  displayName: localStorage.getItem("gomoku_display_name") || "",
  theme: localStorage.getItem("gomoku_theme") || "quiet",
  snapshot: null,
  connected: false,
  joined: false,
  errorTimer: null,
};

const els = {
  board: document.getElementById("board"),
  connectionDot: document.getElementById("connectionDot"),
  connectionText: document.getElementById("connectionText"),
  roomLabel: document.getElementById("roomLabel"),
  turnLabel: document.getElementById("turnLabel"),
  moveLabel: document.getElementById("moveLabel"),
  statusBanner: document.getElementById("statusBanner"),
  nameInput: document.getElementById("nameInput"),
  joinButton: document.getElementById("joinButton"),
  youLabel: document.getElementById("youLabel"),
  blackSeat: document.getElementById("blackSeat"),
  whiteSeat: document.getElementById("whiteSeat"),
  blackName: document.getElementById("blackName"),
  whiteName: document.getElementById("whiteName"),
  spectatorLabel: document.getElementById("spectatorLabel"),
  shareLink: document.getElementById("shareLink"),
  copyButton: document.getElementById("copyButton"),
  lanHints: document.getElementById("lanHints"),
  undoButton: document.getElementById("undoButton"),
  undoLabel: document.getElementById("undoLabel"),
  rematchButton: document.getElementById("rematchButton"),
  rematchLabel: document.getElementById("rematchLabel"),
  moveHistory: document.getElementById("moveHistory"),
  themeToggle: document.getElementById("themeToggle"),
};

function applyTheme(theme) {
  state.theme = theme === "classic" ? "classic" : "quiet";
  document.body.dataset.theme = state.theme;
  localStorage.setItem("gomoku_theme", state.theme);
  if (els.themeToggle) {
    els.themeToggle.checked = state.theme === "classic";
    els.themeToggle.setAttribute("aria-label", `${titleCase(state.theme)} theme active`);
  }
}

function bootstrapBoard() {
  els.board.innerHTML = "";
  for (let index = 0; index < BOARD_SIZE; index += 1) {
    addAxisLabel("col top", COL_LABELS[index], 0, index);
    addAxisLabel("col bottom", COL_LABELS[index], BOARD_SIZE - 1, index);
    addAxisLabel("row left", `${index + 1}`, index, 0);
    addAxisLabel("row right", `${index + 1}`, index, BOARD_SIZE - 1);
  }
  for (const [row, col] of STAR_POINTS) {
    const star = document.createElement("span");
    star.className = "star-point";
    star.style.left = `${(col / (BOARD_SIZE - 1)) * 100}%`;
    star.style.top = `${(row / (BOARD_SIZE - 1)) * 100}%`;
    els.board.appendChild(star);
  }
  for (let row = 0; row < BOARD_SIZE; row += 1) {
    for (let col = 0; col < BOARD_SIZE; col += 1) {
      const cell = document.createElement("button");
      cell.className = "cell";
      cell.type = "button";
      cell.dataset.row = row;
      cell.dataset.col = col;
      cell.title = coordinateLabel(row, col);
      cell.style.left = `${(col / (BOARD_SIZE - 1)) * 100}%`;
      cell.style.top = `${(row / (BOARD_SIZE - 1)) * 100}%`;
      cell.addEventListener("click", () => sendMove(row, col));
      els.board.appendChild(cell);
    }
  }
}

function addAxisLabel(className, text, row, col) {
  const label = document.createElement("span");
  label.className = `axis-label ${className}`;
  label.textContent = text;
  label.style.left = `${(col / (BOARD_SIZE - 1)) * 100}%`;
  label.style.top = `${(row / (BOARD_SIZE - 1)) * 100}%`;
  els.board.appendChild(label);
}

async function loadConfig() {
  const response = await fetch("/config");
  const config = await response.json();
  if (!state.roomId) {
    state.roomId = config.default_room;
    const url = new URL(window.location.href);
    url.searchParams.set("room", state.roomId);
    window.history.replaceState({}, "", url);
  }
  const share = new URL(window.location.href);
  share.searchParams.set("room", state.roomId);
  els.shareLink.value = shareUrl(config);
  els.lanHints.innerHTML = config.lan_urls
    .map((url) => {
      const roomUrl = new URL(url);
      roomUrl.searchParams.set("room", state.roomId);
      return `<a href="${roomUrl.toString()}">${roomUrl.toString()}</a>`;
    })
    .join("");
}

function shareUrl(config) {
  const current = new URL(window.location.href);
  current.searchParams.set("room", state.roomId);
  if (!["127.0.0.1", "localhost"].includes(current.hostname)) {
    return current.toString();
  }
  const lanUrl = config.lan_urls.find((url) => {
    const candidate = new URL(url);
    return !["127.0.0.1", "localhost"].includes(candidate.hostname) && !candidate.hostname.startsWith("172.");
  });
  if (!lanUrl) {
    return current.toString();
  }
  const share = new URL(lanUrl);
  share.searchParams.set("room", state.roomId);
  return share.toString();
}

function connect() {
  setConnection("reconnecting", "Connecting...");
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  state.socket = new WebSocket(`${protocol}://${window.location.host}/ws/${encodeURIComponent(state.roomId)}`);

  state.socket.addEventListener("open", () => {
    state.connected = true;
    setConnection("connected", "Connected");
    if (state.displayName) {
      join();
    }
  });

  state.socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    handleMessage(message);
  });

  state.socket.addEventListener("close", () => {
    state.connected = false;
    state.joined = false;
    setConnection("disconnected", "Disconnected");
    window.setTimeout(connect, 1200);
  });
}

function handleMessage(message) {
  if (message.type === "hello") {
    state.playerId = message.player_id;
    state.displayName = message.display_name;
    state.joined = true;
    localStorage.setItem("gomoku_player_id", state.playerId);
    localStorage.setItem("gomoku_display_name", state.displayName);
    els.nameInput.value = state.displayName;
    return;
  }
  if (message.type === "error") {
    showBanner(message.message, true);
    return;
  }
  if (message.type === "snapshot") {
    if (state.snapshot && message.version < state.snapshot.version) {
      return;
    }
    state.snapshot = message;
    renderSnapshot();
  }
}

function join() {
  const name = els.nameInput.value.trim() || state.displayName || "Player";
  state.displayName = name.slice(0, 24);
  send({ type: "join", player_id: state.playerId, display_name: state.displayName });
}

function send(message) {
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
    showBanner("Connection is not ready yet.", true);
    return;
  }
  state.socket.send(JSON.stringify(message));
}

function sendMove(row, col) {
  if (!canMove(row, col)) {
    showBanner(explainBlockedMove(), true);
    return;
  }
  send({ type: "move", row, col });
}

function canMove(row, col) {
  const snap = state.snapshot;
  if (!snap || !state.joined) return false;
  if (snap.game.status !== "playing") return false;
  if (snap.game.board[row][col]) return false;
  return myColor() === snap.game.turn;
}

function explainBlockedMove() {
  const snap = state.snapshot;
  if (!state.joined) return "Enter a name and join first.";
  if (!snap) return "Waiting for the board.";
  if (snap.game.status !== "playing") return "The game is not accepting moves.";
  if (!myColor()) return "Spectators can watch but cannot move.";
  if (myColor() !== snap.game.turn) return "It is not your turn.";
  return "That point is already occupied.";
}

function claimSeat(color) {
  if (!state.joined) {
    showBanner("Enter a name and join before claiming a seat.", true);
    return;
  }
  send({ type: "claim_seat", color });
}

function requestOrAcceptRematch() {
  const snap = state.snapshot;
  if (!snap || !isTerminal(snap.game.status)) return;
  if (snap.rematch_accepts.includes(state.playerId)) {
    showBanner("Waiting for the other player to accept rematch.");
    return;
  }
  const type = snap.rematch_accepts.length === 0 ? "rematch_request" : "rematch_accept";
  send({ type });
}

function requestOrAcceptUndo() {
  const snap = state.snapshot;
  if (!snap || !myColor()) return;
  if (snap.undo_request) {
    if (snap.undo_request.player_id === state.playerId) {
      showBanner("Waiting for the other player to accept undo.");
      return;
    }
    send({ type: "undo_accept" });
    return;
  }
  send({ type: "undo_request" });
}

function renderSnapshot() {
  const snap = state.snapshot;
  els.roomLabel.textContent = snap.room_id;
  els.turnLabel.textContent = titleCase(snap.game.turn);
  els.moveLabel.textContent = snap.game.move_number;
  els.blackName.textContent = seatName(snap.seats.black);
  els.whiteName.textContent = seatName(snap.seats.white);
  els.spectatorLabel.textContent = `Spectators: ${snap.spectators}`;
  els.youLabel.textContent = state.joined ? `You are ${state.displayName}${myColor() ? ` (${titleCase(myColor())})` : " (spectator)"}.` : "You are not joined yet.";
  renderSeats();
  renderBoard();
  renderHistory();
  renderUndo();
  renderRematch();
  showBanner(statusText());
}

function renderSeats() {
  const snap = state.snapshot;
  for (const color of ["black", "white"]) {
    const button = color === "black" ? els.blackSeat : els.whiteSeat;
    const seat = snap.seats[color];
    button.disabled = Boolean(seat) || !state.joined || Boolean(myColor());
    button.classList.toggle("mine", seat?.player_id === state.playerId);
  }
}

function renderBoard() {
  const snap = state.snapshot;
  const lastMove = snap.game.moves.at(-1);
  const winSet = new Set(snap.game.win_line.map((cell) => `${cell.row},${cell.col}`));
  for (const cell of els.board.querySelectorAll(".cell")) {
    const row = Number(cell.dataset.row);
    const col = Number(cell.dataset.col);
    const color = snap.game.board[row][col];
    cell.innerHTML = color ? `<span class="stone ${color}"></span>` : "";
    cell.classList.toggle("legal", canMove(row, col));
    cell.classList.toggle("last", Boolean(lastMove && lastMove.row === row && lastMove.col === col));
    cell.classList.toggle("win", winSet.has(`${row},${col}`));
    cell.style.color = snap.game.turn === "black" ? "#111" : "#fff8e8";
  }
}

function renderHistory() {
  const moves = state.snapshot.game.moves;
  els.moveHistory.innerHTML = moves
    .map((move, index) => `<li><strong>${index + 1}.</strong> ${titleCase(move.color)} ${move.notation}</li>`)
    .join("");
}

function renderRematch() {
  const snap = state.snapshot;
  const terminal = isTerminal(snap.game.status);
  const seated = Boolean(myColor());
  els.rematchButton.disabled = !terminal || !seated;
  els.rematchButton.textContent = snap.rematch_accepts.includes(state.playerId) ? "Waiting..." : snap.rematch_accepts.length ? "Accept rematch" : "Request rematch";
  if (!terminal) {
    els.rematchLabel.textContent = "Rematch appears after a win or draw.";
  } else if (snap.rematch_accepts.length) {
    els.rematchLabel.textContent = `${snap.rematch_accepts.length}/2 players accepted.`;
  } else {
    els.rematchLabel.textContent = "Both seated players must agree.";
  }
}

function renderUndo() {
  const snap = state.snapshot;
  const seated = Boolean(myColor());
  const available = seated && snap.game.status === "playing" && snap.game.move_number > 0;
  els.undoButton.disabled = !available;
  if (!snap.undo_request) {
    els.undoButton.textContent = "Request undo";
    els.undoLabel.textContent = available ? "Ask the other player to take back the latest move." : "Undo is available after a move.";
    return;
  }
  const requester = nameForPlayerId(snap.undo_request.player_id);
  const move = snap.undo_request.move;
  if (snap.undo_request.player_id === state.playerId) {
    els.undoButton.textContent = "Waiting...";
    els.undoLabel.textContent = `Undo requested for ${titleCase(move.color)} ${move.notation}. Waiting for the other player.`;
  } else {
    els.undoButton.textContent = "Accept undo";
    els.undoLabel.textContent = `${requester} wants to undo ${titleCase(move.color)} ${move.notation}.`;
  }
}

function statusText() {
  const snap = state.snapshot;
  if (!state.connected) return "Disconnected. Reconnecting...";
  if (!state.joined) return "Enter a name to join this room.";
  if (!snap.seats.black || !snap.seats.white) return "Claim a seat or wait for another player.";
  if (snap.game.status === "black_win") return "Black wins. Five in a row.";
  if (snap.game.status === "white_win") return "White wins. Five in a row.";
  if (snap.game.status === "draw") return "Draw. The board is full.";
  if (myColor() === snap.game.turn) return "Your turn.";
  if (!myColor()) return "You are watching as a spectator.";
  return `${titleCase(snap.game.turn)} to move.`;
}

function showBanner(message, isError = false) {
  els.statusBanner.textContent = message;
  els.statusBanner.classList.toggle("shake", isError);
  if (isError) {
    window.clearTimeout(state.errorTimer);
    state.errorTimer = window.setTimeout(() => els.statusBanner.classList.remove("shake"), 320);
  }
}

function setConnection(kind, text) {
  els.connectionDot.className = `dot ${kind === "reconnecting" ? "" : kind}`;
  els.connectionText.textContent = text;
}

function seatName(seat) {
  if (!seat) return "Open seat";
  return `${seat.display_name}${seat.connected ? "" : " (reconnecting)"}`;
}

function myColor() {
  const snap = state.snapshot;
  if (!snap) return null;
  if (snap.seats.black?.player_id === state.playerId) return "black";
  if (snap.seats.white?.player_id === state.playerId) return "white";
  return null;
}

function nameForPlayerId(playerId) {
  const snap = state.snapshot;
  for (const color of ["black", "white"]) {
    const seat = snap.seats[color];
    if (seat?.player_id === playerId) {
      return seat.display_name;
    }
  }
  return "Other player";
}

function isTerminal(status) {
  return ["black_win", "white_win", "draw"].includes(status);
}

function titleCase(value) {
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}

function coordinateLabel(row, col) {
  return `${String.fromCharCode("A".charCodeAt(0) + col)}${row + 1}`;
}

els.joinButton.addEventListener("click", join);
els.nameInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") join();
});
els.blackSeat.addEventListener("click", () => claimSeat("black"));
els.whiteSeat.addEventListener("click", () => claimSeat("white"));
els.copyButton.addEventListener("click", async () => {
  await navigator.clipboard.writeText(els.shareLink.value);
  showBanner("LAN link copied.");
});
els.undoButton.addEventListener("click", requestOrAcceptUndo);
els.rematchButton.addEventListener("click", requestOrAcceptRematch);
if (els.themeToggle) {
  els.themeToggle.addEventListener("change", () => applyTheme(els.themeToggle.checked ? "classic" : "quiet"));
}

applyTheme(state.theme);
bootstrapBoard();
els.nameInput.value = state.displayName;
loadConfig().then(connect).catch((error) => {
  setConnection("disconnected", "Config failed");
  showBanner(error.message, true);
});
