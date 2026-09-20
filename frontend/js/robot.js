// Robot Helper: a computer does exactly what it is told, one step after the other. The child builds a
// little program by clicking arrow cards, then presses play and the robot follows it. If the robot does not
// reach the battery it simply walks back to the start, and the child can change the program and try again.
// The levels grow from two cards to a longer program with a "3 steps" card (a first loop).

const ROBOT_ICONS = ["🔋", "🗺️", "🪨", "⏩", "🔋🔋"];

// Cards: what each one does. "R3" and "D3" are the double arrows: the same step three times in a row.
const ROBOT_CARDS = {
  R: { label: "➡️", dx: 1, dy: 0, times: 1 }, L: { label: "⬅️", dx: -1, dy: 0, times: 1 },
  U: { label: "⬆️", dx: 0, dy: -1, times: 1 }, D: { label: "⬇️", dx: 0, dy: 1, times: 1 },
  R3: { label: "⏩", dx: 1, dy: 0, times: 3 }, D3: { label: "⏬", dx: 0, dy: 1, times: 3 },
};
const ARROWS = ["R", "L", "U", "D"];

// cols/rows: size of the garden. start, goals (batteries) and rocks are [x, y] cells. `slots` is how many cards the
// program may have. `solution` is one way to solve it (used for the gentle hints and by the automatic tests).
// `guide`: show which card is next while the child builds the program.
const ROBOT_LEVELS = [
  { text: "robot.l1", cols: 4, rows: 3, start: [0, 1], goals: [[2, 1]], rocks: [], slots: 3, cards: ARROWS, solution: ["R", "R"], guide: true },
  { text: "robot.l2", cols: 5, rows: 3, start: [0, 0], goals: [[3, 2]], rocks: [], slots: 6, cards: ARROWS, solution: ["R", "R", "R", "D", "D"], guide: true },
  { text: "robot.l3", cols: 5, rows: 3, start: [0, 1], goals: [[4, 1]], rocks: [[2, 1]], slots: 7, cards: ARROWS, solution: ["R", "U", "R", "R", "D", "R"], guide: true },
  { text: "robot.l4", cols: 7, rows: 3, start: [0, 1], goals: [[6, 1]], rocks: [], slots: 3, cards: [...ARROWS, "R3"], solution: ["R3", "R3"], guide: false },
  { text: "robot.l5", cols: 5, rows: 4, start: [0, 0], goals: [[4, 0], [4, 3]], rocks: [[2, 0]], slots: 6, cards: [...ARROWS, "R3", "D3"], solution: ["D", "R3", "R", "U", "D3"], guide: false },
];

function robotHelper() {
  levelPicker("robot", "🤖", ROBOT_ICONS, (n) => robotLevel(n, () => completeLevel("robot", n, robotHelper)));
}

function robotLevel(number, done) {
  const level = ROBOT_LEVELS[number - 1];
  const same = (a, b) => a[0] === b[0] && a[1] === b[1];
  let program = [];
  let running = false;

  // ----- the garden -----
  const grid = el("div", { class: "rgrid" });
  grid.style.gridTemplateColumns = `repeat(${level.cols}, 1fr)`;
  grid.style.setProperty("--cols", level.cols);
  grid.style.setProperty("--rows", level.rows);
  const cells = {};
  for (let y = 0; y < level.rows; y++) {
    for (let x = 0; x < level.cols; x++) {
      cells[`${x},${y}`] = el("div", { class: "rcell" });
      grid.append(cells[`${x},${y}`]);
    }
  }
  const robot = el("div", { class: "robot" }, "🤖");
  let at = [...level.start], got = [];
  function drawGarden() {
    Object.values(cells).forEach((cell) => cell.replaceChildren());
    level.rocks.forEach(([x, y]) => cells[`${x},${y}`].append(el("span", {}, "🪨")));
    level.goals.forEach(([x, y]) => { if (!got.some((g) => same(g, [x, y]))) cells[`${x},${y}`].append(el("span", {}, "🔋")); });
    cells[`${at[0]},${at[1]}`].append(robot);
  }

  // ----- the program -----
  const strip = el("div", { class: "rprog" });
  const slots = Array.from({ length: level.slots }, () => el("div", { class: "rslot" }));
  strip.append(...slots);
  const cardRow = el("div", { class: "rcards" });
  const buttons = {};
  for (const name of level.cards) {
    buttons[name] = el("button", { class: "rcard", "data-card": name, "aria-label": name }, ROBOT_CARDS[name].label);
    buttons[name].addEventListener("click", () => add(name));
    cardRow.append(buttons[name]);
  }
  const undo = el("button", { class: "rcard rundo", "aria-label": "undo" }, "↩️");
  const run = el("button", { class: "rcard rrun", "aria-label": "play" }, "▶️");
  cardRow.append(undo, run);

  function drawProgram() {
    slots.forEach((slot, i) => { slot.textContent = program[i] ? ROBOT_CARDS[program[i]].label : ""; slot.classList.toggle("filled", !!program[i]); });
    // The gentle guide: if the cards so far are right, the next card glows; if not, the take-back button does.
    Object.values(buttons).concat([undo, run]).forEach((b) => b.classList.remove("attention-btn"));
    if (!level.guide || running) return;
    const onTrack = program.every((card, i) => card === level.solution[i]);
    if (!onTrack) undo.classList.add("attention-btn");
    else if (program.length === level.solution.length) run.classList.add("attention-btn");
    else buttons[level.solution[program.length]].classList.add("attention-btn");
  }
  function add(name) {
    if (running || program.length >= level.slots) return;
    program.push(name); sfx("tap"); drawProgram();
  }
  undo.addEventListener("click", () => { if (running || !program.length) return; program.pop(); sfx("key"); drawProgram(); });

  // ----- running it -----
  // Every step is one small move; a rock or the edge of the garden just makes the robot stay where it is.
  const steps = () => program.flatMap((name) => Array(ROBOT_CARDS[name].times).fill(ROBOT_CARDS[name]));
  run.addEventListener("click", () => {
    if (running || !program.length) return;
    running = true; drawProgram(); sfx("play");
    const list = steps();
    at = [...level.start]; got = []; drawGarden();
    let i = 0;
    const tick = () => {
      if (i === list.length) return finish();
      const next = [at[0] + list[i].dx, at[1] + list[i].dy];
      const inside = next[0] >= 0 && next[1] >= 0 && next[0] < level.cols && next[1] < level.rows;
      if (inside && !level.rocks.some((r) => same(r, next))) {
        at = next; sfx("note", i % 8);
        if (level.goals.some((g) => same(g, at)) && !got.some((g) => same(g, at))) { got.push([...at]); sfx("sparkle"); }
      } else {
        replayAnimation(robot, "wobble"); sfx("key");
      }
      drawGarden();
      i++;
      later(tick, 450);
    };
    const finish = () => {
      if (got.length === level.goals.length) {
        sfx("success"); robot.classList.add("happy");
        $("#screen").dataset.need = "";
        return later(done, 1100);
      }
      speak(t("robot.again"));                        // not there yet: back to the start, the program stays
      later(() => { at = [...level.start]; got = []; running = false; drawGarden(); drawProgram(); }, 900);
    };
    later(tick, 400);
  });

  const bubble = instruction("🤖", t(level.text));
  setScreen(`robot-${number}`, bubble, grid, strip, cardRow);
  $("#screen").dataset.need = level.solution.join(",");
  drawGarden(); drawProgram();
}
