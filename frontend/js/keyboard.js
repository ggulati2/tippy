// The on-screen keyboard, finger colours, and the gentle "wrong key" reaction.
// Shared by Keyboard Kingdom and Letter Land.

// Keys are named by their capital letter, or SPACE / ENTER / BACKSPACE / SHIFT.
// The parent chooses which shape to draw; the real keyboard always works by what it types.
//
// KEY_ROWS and KEYBOARD_NAMES come from frontend/js/layouts-data.js (loaded just before this file),
// which is generated from frontend/layouts/*.json by scripts/sync_layouts.py. docs/REVAMP_BRIEF.md
// section 4.4 asks that "the on-screen keyboard, finger zones, and lessons all read from one source" —
// that source is the .json files; edit those, then run the script, to add or change a keyboard shape.

// Does this keyboard have a key of its own for this character (Ä Ö Ü on a German one, Ñ on a Spanish one)?
const layoutHas = (name, layout = settings.keyboard_layout) => (KEY_ROWS[layout] || []).some((row) => row.includes(name));

const KEY_LABELS = { SHIFT: "⇧", BACKSPACE: "⌫", ENTER: "⏎", SPACE: "␣", UP: "↑", DOWN: "↓", LEFT: "←", RIGHT: "→", CAPS: "⇪" };

// Small boards for single-key games in Keyboard Kingdom.
const ARROW_ROWS = [["UP"], ["LEFT", "DOWN", "RIGHT"]];
const CAPS_ROWS = [["CAPS"]];
const WIDE_KEYS = ["SHIFT", "BACKSPACE", "ENTER", "CAPS"];

// The number pad, as on the right of a big keyboard. Number Land draws it on screen.
const NUMPAD_ROWS = [["7", "8", "9"], ["4", "5", "6"], ["1", "2", "3"], ["0", ".", "ENTER"]];
// Right-hand fingers on the pad: index (7 4 1), middle (8 5 2), ring (9 6 3), thumb and little finger below.
const NUMPAD_FINGER = { 7: 4, 4: 4, 1: 4, 8: 5, 5: 5, 2: 5, 9: 6, 6: 6, 3: 6, ".": 6, ENTER: 7 };

// While a Number Land screen is showing and the parent said "this computer has a number pad", digits
// from the row above the letters are treated like a wrong key ("use the pad"), so the pad gets practised.
let padOnlyScreen = false;

// One colour per finger, from the left little finger to the right little finger.
const FINGER_COLORS = ["#ff8787", "#ffa94d", "#ffd43b", "#69db7c", "#4dabf7", "#9775fa", "#f783ac", "#38d9a9"];
const THUMB_COLOR = "#dee2e6";

function fingerGroups(layout) {
  // Z and Y swap places on a German keyboard, and so do their fingers.
  const leftZ = layout === "qwertz" ? "Y" : "Z";
  const rightY = layout === "qwertz" ? "Z" : "Y";
  return [
    ["Q", "A", leftZ, "SHIFT"], ["W", "S", "X"], ["E", "D", "C"], ["R", "F", "V", "T", "G", "B"],
    [rightY, "H", "N", "U", "J", "M"], ["I", "K"], ["O", "L"], ["P", "Ü", "Ö", "Ä", "ß", "Ñ", "BACKSPACE", "ENTER"],
  ];
}

function zoneColor(key, layout = settings.keyboard_layout) {
  if (["UP", "DOWN", "LEFT", "RIGHT"].includes(key)) return FINGER_COLORS[4];
  if (key === "CAPS") return FINGER_COLORS[0];
  if (layout === "numpad") return key in NUMPAD_FINGER ? FINGER_COLORS[NUMPAD_FINGER[key]] : THUMB_COLOR;
  const finger = fingerGroups(layout).findIndex((group) => group.includes(key));
  return finger === -1 ? THUMB_COLOR : FINGER_COLORS[finger];
}

// Turn a real key press into one of our key names (or null for keys we ignore).
const SPECIAL_KEYS = { ArrowUp: "UP", ArrowDown: "DOWN", ArrowLeft: "LEFT", ArrowRight: "RIGHT", CapsLock: "CAPS" };

function keyName(e) {
  if (e.key in SPECIAL_KEYS) return SPECIAL_KEYS[e.key];
  if (e.key === "ß") return "ß";        // "ß".toUpperCase() is "SS", so it must not go through the upper-casing below
  if (padOnlyScreen && settings.has_numpad && /^[0-9]$/.test(e.key) && e.code && e.code.startsWith("Digit")) return "NOPAD";
  if (e.key === " ") return "SPACE";
  if (e.key === "Enter") return "ENTER";
  if (e.key === "Backspace") return "BACKSPACE";
  if (e.key === "Shift") return "SHIFT";
  const upper = e.key.length === 1 ? e.key.toUpperCase() : "";
  return upper.length === 1 ? upper : null;
}

// Draws the keyboard. Returns { node, highlight, press, wobble, pulse, has }.
// `rows` draws a small custom board (arrow keys, Caps Lock) instead of a full keyboard.
function renderKeyboard(layout = settings.keyboard_layout, rows = null) {
  const node = el("div", { class: "keyboard" + (layout === "numpad" ? " numpad" : "") });
  const keys = {};
  for (const row of rows || (layout === "numpad" ? NUMPAD_ROWS : KEY_ROWS[layout] || KEY_ROWS.qwerty)) {
    const rowNode = el("div", { class: "key-row" });
    for (const name of row) {
      const key = el("div", { class: "key" + (WIDE_KEYS.includes(name) ? " wide" : "") + (name === "SPACE" ? " space" : "") },
        KEY_LABELS[name] || name);
      key.style.setProperty("--c", zoneColor(name, layout));
      keys[name] = key;
      rowNode.append(key);
    }
    node.append(rowNode);
  }
  // Restarts a one-shot CSS animation on a key.
  const replay = (key, cls) => { key.classList.remove(cls); void key.offsetWidth; key.classList.add(cls); };
  return {
    node,
    has: (name) => name in keys,
    element: (name) => keys[name], // the dashboard heat map colours keys directly
    // The glowing key the child should find. Only one at a time.
    highlight(name) {
      Object.values(keys).forEach((k) => k.classList.remove("goal"));
      if (keys[name]) keys[name].classList.add("goal");
    },
    press(name) { if (keys[name]) replay(keys[name], "pressed"); },
    wobble(name) { if (keys[name]) replay(keys[name], "wobble"); },
    pulse(name) { if (keys[name]) replay(keys[name], "attention"); },
  };
}

const renderNumpad = () => renderKeyboard("numpad");

// Wrong key: never red, never a buzzer. The pressed key wiggles, the right key
// pulses, and every second time Tippy says a friendly hint.
let missCount = 0;
function softMiss(board, target, pressed) {
  if (pressed && board.has(pressed)) board.wobble(pressed);
  board.pulse(target);
  sfx("key");
  if (missCount++ % 2 === 0) speak(t("oopsTry"));
}

// Tell the server how a key press went (for progress and the parent's heat map).
// If it fails, the child never notices: we just carry on.
async function sendKeys(events, adaptive = false) {
  try {
    const { status, body } = await api("/api/keystrokes", { method: "POST", body: JSON.stringify({ events, adaptive }) });
    return status === 200 ? body : null;
  } catch (e) {
    return null;
  }
}

// ---------- Layout mismatch detection (docs/REVAMP_BRIEF.md section 4.4) ----------
// A German QWERTZ keyboard and a US/UK QWERTY keyboard swap the Y and Z keys. If the app is set to one
// but the real, physical keyboard is the other, the child keeps missing the glowing key by exactly one
// letter, which is confusing and not their fault. `e.code` names the physical key position and does not
// change with the layout, while `e.key` is the character the browser actually produced; comparing the
// two (for just this one well-known swap) tells us the two disagree without needing to know what the
// browser or operating system thinks its own layout is called.
const LAYOUT_MISMATCH_STREAK = 5; // a short run of swapped presses, not one lucky or unlucky guess
let layoutMismatchStreak = 0;
let layoutMismatchSent = false;

function trackLayoutMismatch(e) {
  if (layoutMismatchSent || settings.layout_mismatch_flag || !e.code || (e.code !== "KeyY" && e.code !== "KeyZ")) return;
  const expectQwertz = settings.keyboard_layout === "qwertz";
  // On a real QWERTZ keyboard, the key at the "Y position" types Z and vice versa.
  const expectedKey = e.code === "KeyY" ? (expectQwertz ? "Z" : "Y") : (expectQwertz ? "Y" : "Z");
  if (e.key.toUpperCase() === expectedKey) {
    layoutMismatchStreak = 0; // a normal press: the keyboard matches the setting, so far
    return;
  }
  layoutMismatchStreak++;
  if (layoutMismatchStreak < LAYOUT_MISMATCH_STREAK) return;
  layoutMismatchSent = true; // never ask more than once per visit; the parent can dismiss it, too
  // Best effort and silent: the child never sees this, win or lose. The parent sees a gentle note
  // next time they open Settings (see settingsTab in dashboard.js).
  api("/api/layout-mismatch", { method: "POST" }).catch(() => {});
}
