// Paint Place: learn the mouse by painting. Press and hold, move, let go; pick colours and sizes;
// put stamps on the paper; take a mistake back with Undo. Nothing can be done wrong: a wrong colour
// is simply painted anyway, and the right button pulses.
// Nothing painted is saved or sent anywhere.

const PAINT_ICONS = ["🖌️", "🎨", "⭕", "🐱", "🖼️"];
const PAINT_COLOURS = [
  ["red", "#ff6b6b"], ["blue", "#339af0"], ["yellow", "#fcc419"], ["green", "#51cf66"], ["purple", "#9775fa"], ["orange", "#ff922b"],
];
const PAINT_SIZES = [["thin", 5], ["medium", 14], ["thick", 32]];
const PAINT_STAMPS = ["🐱", "🌈", "⭐", "🌸"];

function paintPlace() {
  levelPicker("paint", "🖌️", PAINT_ICONS, (n) => {
    [paintFirst, paintColours, paintSizes, paintStamps, paintFree][n - 1](() => completeLevel("paint", n, paintPlace));
  });
}

// One painting board: a canvas plus the buttons a level asks for.
//   options: { colours, sizes, stamps, undo, clear }  (which tools to show)
// Returns the pieces so a level can watch what the child does.
//   board.node   the whole board (put it on the screen)
//   board.colour / board.size / board.stamp   what is selected now
//   board.onStroke(fn) / board.onStamp(fn) / board.onUndo(fn)
function paintBoard(options) {
  const canvas = el("canvas", { class: "paper", width: "1000", height: "440" });
  const pen = canvas.getContext("2d");
  const state = { colour: "#9775fa", colourName: "purple", size: 14, sizeName: "medium", stamp: null };
  const items = [];                                   // everything painted, so Undo can take the last one back
  const listeners = { stroke: [], stamp: [], undo: [] };

  function redraw() {
    pen.clearRect(0, 0, canvas.width, canvas.height);
    pen.lineCap = "round"; pen.lineJoin = "round";
    for (const item of items) {
      if (item.stamp) {
        pen.font = "90px serif"; pen.textAlign = "center"; pen.textBaseline = "middle";
        pen.fillText(item.stamp, item.x, item.y);
      } else {
        pen.strokeStyle = item.colour; pen.fillStyle = item.colour; pen.lineWidth = item.size;
        pen.beginPath();
        item.points.forEach(([x, y], i) => (i ? pen.lineTo(x, y) : pen.moveTo(x, y)));
        if (item.points.length === 1) { pen.arc(item.points[0][0], item.points[0][1], item.size / 2, 0, 7); pen.fill(); }
        else pen.stroke();
      }
    }
  }
  // Mouse position on the canvas (the canvas is drawn smaller or larger than its 1000 x 440 pixels).
  const spot = (e) => {
    const r = canvas.getBoundingClientRect();
    return [(e.clientX - r.left) * (canvas.width / (r.width || 1)), (e.clientY - r.top) * (canvas.height / (r.height || 1))];
  };
  let current = null;
  canvas.addEventListener("pointerdown", (e) => {
    try { canvas.setPointerCapture(e.pointerId); } catch (err) { /* the mouse works without capture */ }
    const [x, y] = spot(e);
    if (state.stamp) {                                 // a stamp is placed with one click
      items.push({ stamp: state.stamp, x, y });
      redraw(); sfx("tap");
      listeners.stamp.forEach((fn) => fn(items.length));
      return;
    }
    current = { colour: state.colour, colourName: state.colourName, size: state.size, sizeName: state.sizeName, points: [[x, y]], length: 0 };
    items.push(current);
    sfx("key");
    redraw();
  });
  canvas.addEventListener("pointermove", (e) => {
    if (!current) return;
    const [x, y] = spot(e), last = current.points[current.points.length - 1];
    current.length += Math.hypot(x - last[0], y - last[1]);
    current.points.push([x, y]);
    redraw();
  });
  const finish = () => {
    if (!current) return;
    const done = current;
    current = null;
    if (done.length < 25) {                            // a tiny click is not a line: nothing to keep
      items.splice(items.indexOf(done), 1);
      redraw();
    } else {
      listeners.stroke.forEach((fn) => fn(done));
    }
  };
  canvas.addEventListener("pointerup", finish);
  canvas.addEventListener("pointercancel", finish);

  const bar = el("div", { class: "paint-bar" });
  const swatches = {}, sizeButtons = {}, stampButtons = [];
  const mark = () => {
    for (const [name, node] of Object.entries(swatches)) node.classList.toggle("on", !state.stamp && name === state.colourName);
    for (const [name, node] of Object.entries(sizeButtons)) node.classList.toggle("on", !state.stamp && name === state.sizeName);
    stampButtons.forEach((node) => node.classList.toggle("on", node.dataset.stamp === state.stamp));
  };
  if (options.colours) {
    for (const [name, hex] of PAINT_COLOURS.slice(0, options.colours)) {
      const swatch = el("button", { class: "swatch", "data-color": name, "aria-label": name });
      swatch.style.background = hex;
      swatch.addEventListener("click", () => { sfx("tap"); state.colour = hex; state.colourName = name; state.stamp = null; mark(); });
      swatches[name] = swatch;
      bar.append(swatch);
    }
  }
  if (options.sizes) {
    for (const [name, px] of PAINT_SIZES.slice(0, options.sizes)) {
      const dot = el("span", { class: "size-dot" });
      dot.style.width = dot.style.height = Math.max(8, px) + "px";
      const button = el("button", { class: "size-btn", "data-size": name, "aria-label": name }, dot);
      button.addEventListener("click", () => { sfx("tap"); state.size = px; state.sizeName = name; state.stamp = null; mark(); });
      sizeButtons[name] = button;
      bar.append(button);
    }
  }
  if (options.stamps) {
    for (const emoji of PAINT_STAMPS) {
      const button = el("button", { class: "stamp-btn", "data-stamp": emoji }, emoji);
      button.addEventListener("click", () => { sfx("tap"); state.stamp = state.stamp === emoji ? null : emoji; mark(); });
      stampButtons.push(button);
      bar.append(button);
    }
  }
  const undo = el("button", { class: "tool-btn", id: "undo", "aria-label": "undo" }, "↩️");
  undo.addEventListener("click", () => {
    if (!items.length) return;
    items.pop(); redraw(); sfx("boing");
    listeners.undo.forEach((fn) => fn(items.length));
  });
  if (options.undo) bar.append(undo);
  if (options.clear) {
    const clear = el("button", { class: "tool-btn", "aria-label": "clear" }, "🗑️");
    clear.addEventListener("click", () => { items.length = 0; redraw(); sfx("home"); });
    bar.append(clear);
  }
  mark();

  return {
    node: el("div", { class: "paint-board" }, bar, canvas),
    state, swatches, sizeButtons, undoButton: undo,
    count: () => items.length,
    onStroke: (fn) => listeners.stroke.push(fn),
    onStamp: (fn) => listeners.stamp.push(fn),
    onUndo: (fn) => listeners.undo.push(fn),
    pulse: (node) => replayAnimation(node, "attention"),
  };
}

// The tests (and nobody else) read what the next step needs from the screen.
const paintNeeds = (what) => { $("#screen").dataset.need = what; };

// ---------- Level 1: press, hold, move ----------
function paintFirst(done) {
  const total = 3;
  let lines = 0;
  const board = paintBoard({});
  const dots = progressDots(0, total);
  setScreen("paint-1", instruction("🖌️", t("paint.hold")), dots, board.node);
  paintNeeds("stroke");
  board.onStroke(() => {
    if (lines >= total) return;
    lines++;
    sfx("success");
    dots.textContent = progressDots(lines, total).textContent;
    if (lines === total) { paintNeeds(""); later(done, 900); }
  });
}

// ---------- Level 2: colours ----------
function paintColours(done) {
  const tasks = ["red", "blue", "yellow"];
  let step = 0;
  const board = paintBoard({ colours: 6 });
  const dots = progressDots(0, tasks.length);
  const bubble = liveInstruction("🎨", t("paint." + tasks[0]));
  setScreen("paint-2", bubble.node, dots, board.node);
  paintNeeds("colour:" + tasks[0]);
  board.onStroke((stroke) => {
    if (step >= tasks.length) return;                  // the level is finished, a last stroke is just a stroke
    if (stroke.colourName !== tasks[step]) {          // another colour: it is painted anyway, and the right one pulses
      board.pulse(board.swatches[tasks[step]]);
      speak(t("basics.tryAgain"));
      return;
    }
    step++;
    sfx("success");
    dots.textContent = progressDots(step, tasks.length).textContent;
    if (step === tasks.length) { paintNeeds(""); return later(done, 900); }
    bubble.set("🎨", t("paint." + tasks[step]));
    paintNeeds("colour:" + tasks[step]);
  });
}

// ---------- Level 3: thin and thick ----------
function paintSizes(done) {
  const tasks = ["thick", "thin", "thick"];
  let step = 0;
  const board = paintBoard({ colours: 3, sizes: 3 });
  const dots = progressDots(0, tasks.length);
  const bubble = liveInstruction("⭕", t("paint." + tasks[0]));
  setScreen("paint-3", bubble.node, dots, board.node);
  paintNeeds("size:" + tasks[0]);
  board.onStroke((stroke) => {
    if (step >= tasks.length) return;
    // Exactly the size that was asked for counts; any other size is painted anyway, and the right button pulses.
    if (stroke.sizeName !== tasks[step]) {
      board.pulse(board.sizeButtons[tasks[step]]);
      speak(t("basics.tryAgain"));
      return;
    }
    step++;
    sfx("success");
    dots.textContent = progressDots(step, tasks.length).textContent;
    if (step === tasks.length) { paintNeeds(""); return later(done, 900); }
    bubble.set("⭕", t("paint." + tasks[step]));
    paintNeeds("size:" + tasks[step]);
  });
}

// ---------- Level 4: stamps and Undo ----------
function paintStamps(done) {
  const board = paintBoard({ stamps: true, undo: true });
  const dots = progressDots(0, 3);
  const bubble = liveInstruction("🐱", t("paint.stamp"));
  setScreen("paint-4", bubble.node, dots, board.node);
  paintNeeds("stamp");
  let placed = 0, undone = false;
  board.onStamp((count) => {
    placed = count;
    dots.textContent = progressDots(Math.min(count, 3), 3).textContent;
    sfx("sparkle");
    if (count >= 3 && !undone) {                      // three on the paper: now the way back
      bubble.set("↩️", t("paint.undo"));
      board.pulse(board.undoButton);
      paintNeeds("undo");
    }
  });
  board.onUndo(() => {
    if (placed < 3 || undone) return;
    undone = true;
    paintNeeds("");
    later(done, 900);
  });
}

// ---------- Level 5: paint anything ----------
function paintFree(done) {
  const board = paintBoard({ colours: 6, sizes: 3, stamps: true, undo: true, clear: true });
  const ready = el("button", { class: "big-btn play-btn paint-done", "aria-label": "done", disabled: "" }, "✔");
  setScreen("paint-5", instruction("🖼️", t("paint.free")), board.node, ready);
  paintNeeds("free");
  const check = () => { ready.disabled = board.count() < 2; };
  board.onStroke(check); board.onStamp(check); board.onUndo(check);
  ready.addEventListener("click", () => { sfx("success"); paintNeeds(""); later(done, 400); });
}
