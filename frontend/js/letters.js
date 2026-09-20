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

// Bonus rounds: fixed groups of keys (no adaptive difficulty): the top row, the bottom row, and big
// and small letters mixed. The letters come from the keyboard shape in use.
const rowLetters = (row) => (KEY_ROWS[settings.keyboard_layout] || KEY_ROWS.qwerty)[row].filter((k) => k.length === 1);
const LETTER_BONUS = {
  6: { letters: () => rowLetters(0), text: "letters.top", icon: "🔝", mixedCase: false },
  7: { letters: () => rowLetters(2), text: "letters.bottom", icon: "⬇️", mixedCase: false },
  8: { letters: () => [...rowLetters(0), ...rowLetters(1), ...rowLetters(2)], text: "letters.case", icon: "🔠", mixedCase: true },
};

function startLetterGroupRound(round) {
  const { letters: group, text, icon, mixedCase } = LETTER_BONUS[round];
  const letters = group();
  let count = 0, target = "", shownAt = 0, busy = false;
  const board = renderKeyboard();
  const tile = el("button", { class: "big-letter", onclick: () => speak(target) });
  const dots = progressDots(0, LETTERS_PER_ROUND);
  setScreen("letters", instruction(icon, t(text)), tile, dots, board.node);

  function next() {
    let pick;
    do { pick = letters[Math.floor(Math.random() * letters.length)]; } while (pick === target && letters.length > 1);
    target = pick;
    // Big and small letters: the shape changes, the key stays the same.
    tile.textContent = mixedCase ? (Math.random() < 0.5 ? target : target.toLowerCase()) : showCase(target);
    tile.style.background = zoneColor(target);
    replayAnimation(tile, "letter-in");
    board.highlight(target);
    shownAt = performance.now();
    busy = false;
  }
  next();

  keyHandler = (e) => {
    const key = keyName(e);
    if (!key || busy) return;
    const correct = key === target;
    sendKeys([{ key: target, correct, ms: Math.round(performance.now() - shownAt) }]);
    if (!correct) return softMiss(board, target, key);
    busy = true;
    board.press(key);
    sfx("tap");
    count++;
    dots.textContent = progressDots(count, LETTERS_PER_ROUND).textContent;
    if (count === LETTERS_PER_ROUND) { keyHandler = null; return later(() => completeLevel("letters", round, letterLand), 600); }
    later(next, 250);
  };
}

// German only: words with Ä, Ö, Ü and ß, typed with those keys (QWERTZ keyboard).
async function startUmlautRound() {
  const { status, body } = await api("/api/content/special?set=umlaut_words&count=5");
  if (status !== 200 || !body.items.length) throw new Error("no umlaut words available");
  typingRound({
    screen: "words", icon: "Ä", text: t("de.umlauts"),
    items: body.items.map((word) => ({ text: shout(word), speak: word, picture: body.pictures[word] })),
    onDone: () => completeLevel("letters", 9, letterLand),
  });
}

async function startLetterRound(round) {
  if (round === 9) return startUmlautRound();
  if (LETTER_BONUS[round]) return startLetterGroupRound(round);
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
    const serial = screenSerial;             // the answer may arrive after the child has already left this screen
    const result = await sendKeys(events, true);
    events = [];
    let pause = 250;
    if (result) {
      letters = result.letters;
      if (result.change === "advance") { // a new letter is coming: celebrate it
        const fresh = letters[letters.length - 1];
        note.textContent = `✨ ${t("newLetter")} ${showCase(fresh)}`;
        sfx("sparkle");
        if (serial === screenSerial) speak(t("newLetter"));
        pause = 1600;
      } else {
        note.textContent = " ";
      }
    }
    if (count === LETTERS_PER_ROUND) { keyHandler = null; return later(() => completeLevel("letters", round, letterLand), 600); }
    later(next, pause);
  };
}
