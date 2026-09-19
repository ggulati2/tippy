// Number Land: digits and the number pad. Six short games:
//   1 find the number, 2 count and type it, 3 numbers in order, 4 add up, 5 big numbers, 6 count down.
// The on-screen number pad is always shown. Either the number-pad keys or the row of digits above the
// letters work, unless the parent said "this computer has a number pad" (then the row of digits gets a
// friendly hint to use the pad). A wrong key is never punished: the right key pulses.

const NUMBER_ICONS = ["🔢", "🍎", "🚂", "➕", "🔟", "🚀"];
const COUNT_THINGS = ["🍎", "🐟", "🦆", "🎈", "🐝", "🚗", "🌼", "🐢"];

function numberLand() {
  levelPicker("numbers", "🔢", NUMBER_ICONS, (n) => {
    [levelFindNumber, levelCountThings, levelNumbersInOrder, levelAddUp, levelBigNumbers, levelCountdown][n - 1](
      () => completeLevel("numbers", n, numberLand));
  });
}

const randomDigit = (min = 0, max = 9) => Math.floor(min + Math.random() * (max - min + 1));

// Shared by games 1, 2 and 4: a number of rounds, each with one digit as the answer.
// makeRound() returns { answer, nodes, glow }. With glow the answer key lights up (finding a number);
// without it the child works it out (counting, adding), and a wrong key only points at the right one.
function answerRounds(done, { screen, icon, text, total, makeRound }) {
  const board = renderNumpad();
  const scene = el("div", { class: "num-scene" });
  const dots = progressDots(0, total);
  setScreen(screen, instruction(icon, text), scene, dots, board.node);
  padOnlyScreen = true;
  let count = 0, answer = "", shownAt = 0, last = "", busy = false;

  function next() {
    let round;
    do { round = makeRound(); } while (String(round.answer) === last);
    answer = last = String(round.answer);
    scene.replaceChildren(...round.nodes);
    $("#screen").dataset.answer = answer;
    board.highlight(round.glow ? answer : null);
    shownAt = performance.now();
    busy = false;
  }
  next();

  keyHandler = (e) => {
    const key = keyName(e);
    if (!key || busy) return;
    const correct = key === answer;
    sendKeys([{ key: answer, correct, ms: Math.round(performance.now() - shownAt) }]);
    if (!correct) return softMiss(board, answer, key);
    busy = true;                                  // a short pause so the child sees the answer come true
    board.press(key);
    sfx("note", count);
    speak(answer);
    count++;
    dots.textContent = progressDots(count, total).textContent;
    if (count === total) { keyHandler = null; return later(done, 900); }
    later(next, 700);
  };
}

const bigDigit = (digit, glow) => {
  const tile = el("div", { class: "big-letter" }, String(digit));
  tile.style.background = zoneColor(String(digit), "numpad");
  return [tile];
};

// ---------- 1. Find the number ----------
function levelFindNumber(done) {
  answerRounds(done, {
    screen: "nums-1", icon: "🔢", text: t("nums.find"), total: 6,
    makeRound: () => { const d = randomDigit(); return { answer: d, glow: true, nodes: bigDigit(d) }; },
  });
}

// ---------- 2. Count and type ----------
function levelCountThings(done) {
  answerRounds(done, {
    screen: "nums-2", icon: "🍎", text: t("nums.count"), total: 6,
    makeRound: () => {
      const n = randomDigit(1, 9), thing = COUNT_THINGS[randomDigit(0, COUNT_THINGS.length - 1)];
      return { answer: n, glow: false, nodes: [el("div", { class: "count-things" }, thing.repeat(n))] };
    },
  });
}

// ---------- 4. Add up ----------
function levelAddUp(done) {
  answerRounds(done, {
    screen: "nums-4", icon: "➕", text: t("nums.add"), total: 6,
    makeRound: () => {
      const a = randomDigit(1, 5), b = randomDigit(1, 9 - a), thing = COUNT_THINGS[randomDigit(0, COUNT_THINGS.length - 1)];
      return { answer: a + b, glow: false, nodes: [el("div", { class: "count-things" },
        el("span", {}, thing.repeat(a)), el("span", { class: "plus" }, "+"), el("span", {}, thing.repeat(b)))] };
    },
  });
}

// ---------- 3 and 5. Type numbers (the shared typing game with the number pad) ----------
function typeNumbers(done, screen, icon, text, numbers) {
  typingRound({
    screen, icon, text, numpad: true, onDone: done,
    items: numbers.map((n) => ({ text: n, speak: [...n].join(" ") })),   // "1 2 3": read digit by digit
  });
}

function levelNumbersInOrder(done) {
  typeNumbers(done, "nums-3", "🚂", t("nums.order"), ["123", "345", "567", "789", "012"]);
}

function levelBigNumbers(done) {
  typeNumbers(done, "nums-5", "🔟", t("nums.big"), ["10", "12", "15", "18", "20"]);
}

// ---------- 6. Count down and blast off ----------
function levelCountdown(done) {
  const sequence = ["5", "4", "3", "2", "1", "0"];
  let index = 0, shownAt = performance.now();
  const board = renderNumpad();
  const rocket = el("div", { class: "scene-item rocket" }, "🚀");
  const big = el("div", { class: "big-letter" }, sequence[0]);
  const dots = progressDots(0, sequence.length);
  setScreen("nums-6", instruction("🚀", t("nums.countdown")), el("div", { class: "scene" }, rocket), big, dots, board.node);
  padOnlyScreen = true;
  big.style.background = zoneColor(sequence[0], "numpad");
  board.highlight(sequence[0]);

  keyHandler = (e) => {
    const key = keyName(e);
    if (!key) return;
    const target = sequence[index];
    sendKeys([{ key: target, correct: key === target, ms: Math.round(performance.now() - shownAt) }]);
    if (key !== target) return softMiss(board, target, key);
    board.press(key);
    sfx("note", index);
    speak(target);
    index++;
    shownAt = performance.now();
    dots.textContent = progressDots(index, sequence.length).textContent;
    if (index === sequence.length) {                 // 0: blast off!
      keyHandler = null;
      board.highlight(null);
      replayAnimation(rocket, "fly");
      sfx("sparkle");
      return later(done, 1500);
    }
    big.textContent = sequence[index];
    big.style.background = zoneColor(sequence[index], "numpad");
    board.highlight(sequence[index]);
  };
}
