// Letter Land: type the big letter. The server decides which letters are
// unlocked (see backend/difficulty.py): it starts with A and S, adds more as
// the child gets them right, and quietly steps back if things get hard.

const LETTER_ROUND_ICONS = ["🐝", "🐞", "🦋", "🐌", "🐢"];
const LETTERS_PER_ROUND = 10;

const showCase = (letter) => (settings.letter_case === "lower" ? letter.toLowerCase() : letter);

async function letterLand() {
  const { body } = await api("/api/letters");
  // A row of coloured tiles: the letters the child has so far.
  const strip = el("div", { class: "letter-strip" }, ...body.letters.map((letter) => {
    const chip = el("span", { class: "chip letter-chip" }, showCase(letter));
    chip.style.background = zoneColor(letter);
    return chip;
  }));
  levelPicker("letters", "🔤", LETTER_ROUND_ICONS, startLetterRound, strip);
}

async function startLetterRound(round) {
  let { body: info } = await api("/api/letters");
  let letters = info.letters;
  let count = 0, target = null, shownAt = 0, events = [], busy = false;

  const board = renderKeyboard();
  const note = el("div", { class: "note" }, " "); // "new letter" message goes here
  const tile = el("button", { class: "big-letter", onclick: () => speak(target) });
  const dots = progressDots(0, LETTERS_PER_ROUND);
  setScreen("letters", instruction("⌨️", t("kb.find")), note, tile, dots, board.node);

  function next() {
    // The newest letter comes up more often so it gets plenty of practice.
    const newest = letters[letters.length - 1];
    let pick;
    do { pick = Math.random() < 0.4 ? newest : letters[Math.floor(Math.random() * letters.length)]; }
    while (pick === target && letters.length > 1);
    target = pick;
    tile.textContent = showCase(target);
    tile.style.background = zoneColor(target);
    replayAnimation(tile, "letter-in");
    board.highlight(target);
    shownAt = performance.now();
    busy = false;
  }
  next();

  keyHandler = async (e) => {
    const key = keyName(e);
    if (!key || busy) return;
    const ms = Math.round(performance.now() - shownAt);
    if (key !== target) {
      events.push({ key: target, correct: false, ms });
      return softMiss(board, target, key);
    }
    busy = true; // ignore key presses while we save and move on
    events.push({ key: target, correct: true, ms });
    board.press(key);
    sfx("tap");
    count++;
    dots.textContent = progressDots(count, LETTERS_PER_ROUND).textContent;
    const result = await sendKeys(events, true);
    events = [];
    let pause = 250;
    if (result) {
      letters = result.letters;
      if (result.change === "advance") { // a new letter is coming: celebrate it
        const fresh = letters[letters.length - 1];
        note.textContent = `✨ ${t("newLetter")} ${showCase(fresh)}`;
        sfx("sparkle");
        speak(t("newLetter"));
        pause = 1600;
      } else {
        note.textContent = " ";
      }
    }
    if (count === LETTERS_PER_ROUND) { keyHandler = null; return later(() => completeLevel("letters", round, letterLand), 600); }
    later(next, pause);
  };
}
