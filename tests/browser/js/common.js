// Shared helpers for the browser tests. The test page loads this file, then one test script.
// The result is written as JSON into a hidden result element, and tests/browser/test_browser.py reads it.
(() => {
const T = window.T = { results: [], errors: [] };
const pre = document.createElement("pre");
pre.id = "botresult";
document.body.append(pre);
const render = () => { pre.textContent = JSON.stringify({ results: T.results, errors: [...new Set(T.errors)] }); };

// Anything the page reports as an error is a test failure.
window.addEventListener("error", (e) => { T.errors.push("JS error: " + e.message + " (screen " + T.name() + ") " + String(e.error && e.error.stack).split("\n").slice(0, 3).join(" | ")); render(); });
window.addEventListener("unhandledrejection", (e) => { T.errors.push("Unhandled rejection: " + (e.reason && e.reason.message || e.reason)); render(); });
console.error = (...a) => { T.errors.push("console.error: " + a.join(" ")); render(); };
// The page's Content-Security-Policy forbids inline scripts and styles. A page that breaks it is a bug.
document.addEventListener("securitypolicyviolation", (e) => { T.errors.push("CSP violation: " + e.violatedDirective + " " + e.blockedURI + " " + (e.sourceFile || "") + ":" + e.lineNumber); render(); });
Element.prototype.setPointerCapture = () => {};   // synthetic pointer events have no real pointer to capture

T.check = (label, ok, detail = "") => { T.results.push({ label, ok: !!ok, detail: String(detail) }); render(); };
T.wait = (ms) => new Promise((r) => setTimeout(r, ms));
// Wait until something is true (checked every 50 ms of fake time). Needed for things the fake clock cannot
// speed up, such as reading a file: the clock runs ahead of the browser's real work, so the limit must be
// generous (fake time is nearly free, and the loop ends as soon as the condition is true).
T.until = async (condition, ms = 250000) => { for (let t = 0; t < ms / 50 && !condition(); t++) await T.wait(50); return !!condition(); };
T.name = () => document.querySelector("#screen")?.dataset.name || "";
T.modalCount = () => document.querySelector("#modal-root").children.length;
// A real Caps Lock press. On a Mac the browser sends only a keydown when the light goes ON and only a keyup when it
// goes OFF; on Windows and Linux every press sends both. (The first version of the game was tested with a plain keydown
// every time, which only works on Windows: on a Mac it stopped after the first press.)
T.capsState = false;
T.capsPress = (style = T.capsStyle || "mac") => {
  T.capsState = !T.capsState;
  const init = { key: "CapsLock", code: "CapsLock", bubbles: true, cancelable: true, modifierCapsLock: T.capsState };
  const down = () => document.dispatchEvent(new KeyboardEvent("keydown", init));
  const up = () => document.dispatchEvent(new KeyboardEvent("keyup", init));
  if (style === "windows") { down(); up(); } else if (T.capsState) down(); else up();
};
T.key = (k, extra = {}) => { if (k === "CapsLock" && !extra.raw) return T.capsPress(); const e = new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true, ...extra }); document.dispatchEvent(e); return e; };
T.center = (n) => { const r = n.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };
T.pointer = (n, type, [x, y]) => n.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: y, pointerId: 1 }));
T.post = (path, body, headers = {}) => fetch(path, { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body) }).then((r) => r.json());
T.parentLogin = async (pin = "2468") => ({ "X-Parent-Token": (await T.post("/api/parent/verify", { pin })).token });
T.run = async (fn) => { try { await fn(); } catch (e) { T.check("test script crashed", false, e && e.stack || e); } T.check("finished", true); };

// The key the screen is asking for (the glowing one), as a real keyboard event key.
const labelToName = Object.fromEntries(Object.entries(KEY_LABELS).map(([k, v]) => [v, k]));
const toKey = { SPACE: " ", ENTER: "Enter", BACKSPACE: "Backspace", SHIFT: "Shift", UP: "ArrowUp", DOWN: "ArrowDown", LEFT: "ArrowLeft", RIGHT: "ArrowRight", CAPS: "CapsLock" };
T.goalKey = () => {
  const g = document.querySelector(".key.goal");
  if (!g) return null;
  const n = labelToName[g.textContent.trim()] || g.textContent.trim();
  return toKey[n] || n;
};

// Checks once per screen that nothing is cut off by the window edge.
const seen = new Set();
T.checkFit = (n) => {
  if (seen.has(n)) return; seen.add(n);
  const sc = document.querySelector("#screen");
  const problems = [];
  if (sc.scrollHeight > sc.clientHeight + 2) problems.push(`needs scrolling (${sc.scrollHeight} > ${sc.clientHeight})`);
  for (const b of sc.querySelectorAll("button")) {
    const r = b.getBoundingClientRect();
    if (r.width && !b.classList.contains("chest") && (r.bottom > innerHeight + 2 || r.right > innerWidth + 2 || r.left < -2)) { problems.push("a button is off screen: " + (b.textContent || "").slice(0, 10)); break; }
  }
  T.check("fit: " + n, problems.length === 0, problems.join("; "));
};

// Do one sensible action on the current game screen, like a child who plays it right.
// `mistakes`: sometimes press a wrong key or drop on a wrong basket, the way a child does.
T.act = async ({ mistakes = false, doubleClickClose = false } = {}) => {
  const n = T.name(), q = (s) => document.querySelector(s);
  if (n === "mouse-1") q(".balloon:not(:disabled)")?.click();
  else if (n === "mouse-2") {
    const item = q(".draggable"); if (!item) return;
    const shape = item.dataset.shape;
    if (mistakes && !T.act.droppedWrong) {
      T.act.droppedWrong = true;
      const wrong = [...document.querySelectorAll(".basket")].find((b) => b.dataset.shape !== shape);
      T.pointer(item, "pointerdown", T.center(item)); T.pointer(item, "pointerup", T.center(wrong));
      await T.wait(50);
      T.check("dropping on the wrong basket points at the right one", !!q(".basket.hint"));
      return;
    }
    T.pointer(item, "pointerdown", T.center(item)); T.pointer(item, "pointerup", T.center(q(`.basket[data-shape="${shape}"]`)));
  } else if (n === "mouse-3") {
    const egg = q(".egg:not(:disabled)"); if (!egg) return;
    egg.click(); await T.wait(30);                                   // a single click only wiggles
    if (egg.disabled) T.check("a single click must not hatch the egg", false);
    egg.dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
  } else if (n === "mouse-4") q(".chest:not(:disabled)")?.click();
  else if (n === "basics-2") {
    q(".app-icon")?.click();
    const x = q(".close-x"), dots = q(".dots");
    if (x && !x.closest(".fake-window").classList.contains("closing")) {   // only a window that is still open
      const filled = () => dots.textContent.split("●").length - 1;
      const before = filled();
      x.click(); if (doubleClickClose) x.click();          // a child often double-clicks the close button
      T.check("closing the window counts once, even when double-clicked", filled() - before === 1, `${before} -> ${filled()} dots`);
    }
  }
  else if (n.startsWith("basics-")) {
    const cards = [...document.querySelectorAll(".choice:not(:disabled)")];
    if (cards.length) cards[Math.floor(Math.random() * cards.length)].click();   // wrong ones must be harmless
  } else if (n.startsWith("nums-") && document.querySelector("#screen").dataset.answer) {
    T.key(document.querySelector("#screen").dataset.answer);   // counting and adding: the page tells the test the answer
  } else if (n === "free") { for (const c of "cat") T.key(c); T.key("Enter"); await T.wait(200); }
  else {
    const k = T.goalKey(); if (!k) return;
    if (mistakes && Math.random() < 0.15) { T.key(k === "z" ? "q" : "z"); return; }
    T.key(k);
  }
};
})();
