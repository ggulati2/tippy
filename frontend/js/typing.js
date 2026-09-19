// The typing engine shared by Word Woods and Sentence Sky.
//
// The child sees the text as faded "ghost" letters and copies it. The next key
// glows on the on-screen keyboard. A wrong key never hurts: it gets the same
// friendly hint as everywhere else (see softMiss in keyboard.js).

// Which on-screen key does this character need? (null = we cannot ask a child to type it)
function keyForChar(ch) {
  if (ch === " ") return "SPACE";
  const upper = ch.toUpperCase();
  if (/^[A-Z]$/.test(upper)) return upper;
  // Ä, Ö and Ü are real keys on a German keyboard only.
  if ("ÄÖÜ".includes(upper) && settings.keyboard_layout === "qwertz") return upper;
  return null;
}

// Remove punctuation and extra spaces: "The cat sat." becomes "The cat sat".
// Children type the words, not the full stop.
function typingText(text) {
  return text.replace(/[.,!?;:"'\-]/g, "").replace(/\s+/g, " ").trim();
}

// True if every character of the text can be typed.
const isTypable = (text) => text.length > 0 && [...text].every((ch) => keyForChar(ch) !== null);

// Only these key names are accepted by the server's statistics.
const STAT_KEY = /^([A-Z]|SPACE)$/;

const showLetter = (ch) => (settings.letter_case === "lower" ? ch.toLowerCase() : ch.toUpperCase());

// items: [{ text: "cat", speak: "cat", picture: "🐱" (optional) }, ...]
// Plays them one after another, then calls onDone().
function typingRound({ screen, icon, text, items, onDone }) {
  const board = renderKeyboard();
  const hasPictures = items.some((item) => item.picture);
  const picture = el("button", { class: "picture", onclick: () => speak(items[index].speak) });
  const line = el("div", { class: "typing-line" });
  const dots = progressDots(0, items.length);
  const nodes = [instruction(icon, text)];
  if (hasPictures) nodes.push(picture);
  nodes.push(line, dots, board.node);
  setScreen(screen, ...nodes);

  let index = 0, pos = 0, slots = [], events = [], shownAt = 0, busy = false;

  function load() {
    const item = items[index];
    picture.textContent = item.picture || "";
    replayAnimation(picture, "letter-in");
    // Letters are grouped by word, so a long sentence wraps between words, never inside one.
    const parts = [];
    let word = null;
    slots = [...item.text].map((ch) => {
      const slot = el("span", { class: ch === " " ? "slot gap" : "slot" }, ch === " " ? "␣" : showLetter(ch));
      if (ch === " ") { word = null; parts.push(slot); }
      else {
        if (!word) { word = el("span", { class: "word" }); parts.push(word); }
        word.append(slot);
      }
      return slot;
    });
    line.replaceChildren(...parts);
    pos = 0;
    markNext();
    shownAt = performance.now();
    busy = false;
  }

  function markNext() {
    slots.forEach((slot) => slot.classList.remove("now"));
    slots[pos].classList.add("now");
    board.highlight(keyForChar(items[index].text[pos]));
  }

  keyHandler = (e) => {
    const key = keyName(e);
    if (!key || busy) return;
    const item = items[index];
    const expected = keyForChar(item.text[pos]);
    const ms = Math.round(performance.now() - shownAt);
    if (key !== expected) {
      events.push({ key: expected, correct: false, ms });
      return softMiss(board, expected, key);
    }
    events.push({ key: expected, correct: true, ms });
    board.press(key);
    slots[pos].classList.remove("now");
    slots[pos].classList.add("typed");
    if (expected !== "SPACE") slots[pos].style.background = zoneColor(expected);
    sfx("note", pos); // each letter is a step up the scale
    pos++;
    shownAt = performance.now();
    if (pos < item.text.length) return markNext();

    // Finished this word or sentence.
    busy = true;
    board.highlight(null);
    sendKeys(events.filter((event) => STAT_KEY.test(event.key)));
    events = [];
    dots.textContent = progressDots(index + 1, items.length).textContent;
    sfx("success");
    replayAnimation(picture, "jump-up");
    speak(item.speak); // read it aloud after success
    setTimeout(() => {
      index++;
      if (index === items.length) { keyHandler = null; onDone(); } else load();
    }, 1800);
  }

  load();
}
