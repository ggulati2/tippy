// Free Play Studio: a safe typing canvas. The child types any word and presses
// Enter (or the ✨ button). If we know the word (cat, pizza, rainbow) it turns
// into a scene of dancing stickers; otherwise the letters themselves dance.
//
// Everything happens on this computer. The typed text is never sent anywhere.

const MAX_FREE_CHARS = 14;
const SPRITE_MOVES = ["float", "hop", "spin", "sway"];
const SCENES_FOR_STICKER = 3; // the first time the child makes 3 scenes, a sticker is earned

async function freePlay() {
  const { body: pictures } = await api("/api/pictures");
  await loadProgress();
  let text = "";
  let scenes = 0;

  const canvas = el("div", { class: "canvas" }, el("span", { class: "canvas-hint" }, "🎨"));
  const typed = el("div", { class: "free-text" });
  const board = renderKeyboard();
  const magicButton = el("button", { class: "big-btn magic", "aria-label": "magic", onclick: magic }, "✨");
  const clearButton = el("button", { class: "big-btn round", "aria-label": "clear", onclick: clear }, "🗑️");
  setScreen("free", instruction("🎨", t("free.type")), canvas,
    el("div", { class: "free-row" }, typed, magicButton, clearButton), board.node);
  drawText();

  function drawText() {
    typed.replaceChildren(...[...text].map((ch) => {
      const tile = el("span", { class: "slot typed" }, ch === " " ? "␣" : showLetter(ch));
      if (ch !== " ") tile.style.background = zoneColor(ch.toUpperCase());
      return tile;
    }), el("span", { class: "caret" }));
    board.highlight(text ? "ENTER" : null); // once there are letters, point at Enter
  }

  function clear() {
    text = "";
    canvas.replaceChildren(el("span", { class: "canvas-hint" }, "🎨"));
    sfx("key");
    drawText();
  }

  // Typed words carry no accents ("leon"), so look them up without accents. "cats" should still find "cat".
  const plain = (s) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  const plainPictures = Object.fromEntries(Object.entries(pictures).map(([word, emoji]) => [plain(word), emoji]));
  function pictureFor(word) {
    const w = plain(word);
    return plainPictures[w] || (w.endsWith("s") ? plainPictures[w.slice(0, -1)] : undefined);
  }

  function sprite(emoji) {
    const node = el("span", { class: "sprite " + SPRITE_MOVES[Math.floor(Math.random() * SPRITE_MOVES.length)] }, emoji);
    node.style.left = rand(4, 88) + "%";
    node.style.top = rand(6, 78) + "%";
    node.style.fontSize = rand(2.6, 5.2) + "rem";
    node.style.animationDelay = rand(0, 1.2) + "s";
    node.style.animationDuration = rand(1.6, 3) + "s";
    return node;
  }

  function magic() {
    const words = text.trim().toLowerCase().split(" ").filter(Boolean);
    if (!words.length) { sfx("key"); return board.pulse("A"); }
    const emojis = words.map(pictureFor).filter(Boolean).slice(0, 3);
    const parts = [];
    if (emojis.length) {
      for (let i = 0; i < 14; i++) parts.push(sprite(emojis[i % emojis.length]));
    } else {
      // A word we have no picture for: the letters put on a show instead.
      const dancers = el("div", { class: "dancers" }, ...[...text.trim()].map((ch, i) => {
        const tile = el("span", { class: "dancer" }, ch === " " ? " " : showLetter(ch));
        tile.style.animationDelay = i * 0.12 + "s";
        tile.style.color = ch === " " ? "inherit" : zoneColor(ch.toUpperCase());
        return tile;
      }));
      parts.push(dancers, ...["⭐", "✨", "🎈", "💛", "🎉", "🌈"].map(sprite));
    }
    canvas.replaceChildren(...parts);
    $("#screen").append(confetti());
    sfx("sparkle");
    setTimeout(() => sfx("success"), 300);
    speak(text.trim());
    text = ""; // the scene stays on the canvas; the next word starts fresh
    drawText();
    scenes++;
    // A little reward the first time: a sticker for making a few scenes.
    if (scenes === SCENES_FOR_STICKER && !progress.worlds.free.levels[1]) {
      keyHandler = null;
      later(() => completeLevel("free", 1, freePlay), 3000);
    }
  }

  keyHandler = (e) => {
    const key = keyName(e);
    if (key === "ENTER") return magic();
    if (key === "BACKSPACE") {
      text = text.slice(0, -1);
      sfx("key");
    } else if (key && text.length < MAX_FREE_CHARS && keyForChar(key === "SPACE" ? " " : key) !== null) {
      if (key === "SPACE" && (!text || text.endsWith(" "))) return; // no leading or double spaces
      text += key === "SPACE" ? " " : key.toLowerCase();
      board.press(key);
      sfx("note", text.length - 1);
    } else {
      return;
    }
    drawText();
  };
}
