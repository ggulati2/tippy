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
  else if (n.startsWith("paint-")) await T.actPaint(mistakes);
  else if (n.startsWith("desktop-") && (q("#screen").dataset.need || "")) await T.actDesktop();
  else if (n.startsWith("internet-") && (q("#screen").dataset.need || "")) await T.actInternet();
  else if (n.startsWith("robot-")) await T.actRobot(mistakes);
  else if (n.startsWith("basics-") || n.endsWith("-choose") || n === "internet-4") {
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

// ----- the everyday-computer worlds (paint, desktop, internet, robot) -----
// The page says what its next step needs in #screen[data-need]; these play that step like a child would.
T.stroke = async (canvas, from = 0.2, to = 0.8) => {
  const r = canvas.getBoundingClientRect(), y = r.top + r.height * 0.5;
  T.pointer(canvas, "pointerdown", [r.left + r.width * from, y]);
  for (let i = 1; i <= 6; i++) T.pointer(canvas, "pointermove", [r.left + r.width * (from + (to - from) * i / 6), y + i * 3]);
  T.pointer(canvas, "pointerup", [r.left + r.width * to, y + 18]);
  await T.wait(30);
};
T.actPaint = async (mistakes) => {
  const q = (s) => document.querySelector(s), need = q("#screen").dataset.need || "", canvas = q(".paper");
  if (!canvas || !need) return;
  const [kind, value] = need.split(":");
  if (kind === "colour") {
    if (mistakes && !T.actPaint.wrongColour) {                         // the wrong colour is painted but must not count
      T.actPaint.wrongColour = true;
      const other = [...document.querySelectorAll(".swatch")].find((s) => s.dataset.color !== value);
      other.click(); await T.stroke(canvas);
      T.check("a wrong colour does not count, the right one pulses", q("#screen").dataset.need === need);
    }
    q(`.swatch[data-color="${value}"]`).click(); await T.stroke(canvas);
  } else if (kind === "size") {
    q(`.size-btn[data-size="${value}"]`).click(); await T.stroke(canvas);
  } else if (kind === "stamp") {
    q(".stamp-btn").click();
    const r = canvas.getBoundingClientRect();
    T.pointer(canvas, "pointerdown", [r.left + r.width * (0.2 + Math.random() * 0.6), r.top + r.height * 0.5]); T.pointer(canvas, "pointerup", [r.left + 5, r.top + 5]);
    await T.wait(30);
  } else if (kind === "undo") q("#undo").click();
  else if (kind === "free") {
    const done = q(".paint-done");
    if (done.disabled) { await T.stroke(canvas); await T.stroke(canvas, 0.3, 0.6); }
    T.check("the tick is available after painting", !done.disabled);
    done.click();
  } else await T.stroke(canvas, 0.1 + Math.random() * 0.2, 0.6 + Math.random() * 0.3);      // "stroke": any line
};
T.actDesktop = async () => {
  const q = (s) => document.querySelector(s), need = q("#screen").dataset.need;
  if (need === "dblclick") {
    const f = q(".file-open");
    if (!T.actDesktop.slow) {                                            // a slow child: two clicks half a second apart still open it
      T.actDesktop.slow = true;
      f.click(); await T.wait(1500);
      T.check("one click only selects the file", !q(".win") && f.classList.contains("selected"));
      f.click(); await T.wait(500); f.click(); await T.wait(60);         // (no browser double-click event at all)
      T.check("two slow clicks open the file", !!q(".win"));
      return;
    }
    f.click(); f.dispatchEvent(new MouseEvent("dblclick", { bubbles: true })); await T.wait(60);
  }
  else if (need === "close") { const x = q(".close-x:not(:disabled)"); x?.click(); x?.click(); }
  else if (need === "sort") {
    const item = q(".desk-file.draggable"); if (!item) return;
    if (!T.actDesktop.missed) {                                          // a wrong drop first: it glides home and the folder pulses
      T.actDesktop.missed = true;
      const wrong = [...document.querySelectorAll(".folder")].find((f) => f.dataset.kind !== item.dataset.kind);
      T.pointer(item, "pointerdown", T.center(item)); T.pointer(item, "pointerup", T.center(wrong));
      await T.wait(50);
      T.check("a file dropped in the wrong folder points at the right one", !!q(".folder.hint"));
      return;
    }
    T.pointer(item, "pointerdown", T.center(item)); T.pointer(item, "pointerup", T.center(q(`.folder[data-kind="${item.dataset.kind}"]`)));
  } else if (need === "trash-drag") { const f = q(".desk-file.draggable"); T.pointer(f, "pointerdown", T.center(f)); T.pointer(f, "pointerup", T.center(q(".trash"))); }
  else if (need === "trash-open") q(".trash").click();
  else if (need === "restore") q(".restore-btn").click();
  else if (need === "save") q(".save-btn").click();
  else if (need === "edit") q(".edit-btn").click();
  else if (need === "dialog") {
    q(".dlg-drop").click(); await T.wait(30);
    T.check("choosing not to save keeps the question open", !!q(".dlg-save"));
    q(".dlg-save").click();
  }
  else if (need.startsWith("login:")) {
    const secret = need.slice("login:".length).split(",");
    const tiles = [...document.querySelectorAll(".login-hint ~ .choices .choice:not(:disabled)")];
    if (!T.actDesktop.wrongTap) {                                    // a wrong tap first: it only wobbles, nothing is lost
      T.actDesktop.wrongTap = true;
      const wrong = tiles.find((tile) => tile.textContent !== secret[0]);
      if (wrong) { wrong.click(); await T.wait(50); T.check("tapping the wrong picture only wobbles it", !wrong.disabled); return; }
    }
    const next = tiles.find((tile) => tile.textContent === secret[0]);
    next?.click();
  }
};
T.actInternet = async () => {
  const q = (s) => document.querySelector(s), need = q("#screen").dataset.need || "";
  const [kind, value] = need.split(":");
  if (kind === "link") {
    const wrong = [...document.querySelectorAll(".link-card")].find((c) => c.dataset.page !== value);
    if (!T.actInternet.wobbled) { T.actInternet.wobbled = true; wrong.click(); await T.wait(30); T.check("a wrong link only wobbles", q("#screen").dataset.need === need); }
    q(`.link-card[data-page="${value}"]`).click();
  } else if (kind === "back") q(".br-back").click();
  else if (kind === "star") q(".br-star").click();
  else if (kind === "home") q(".br-home").click();
  else if (kind === "favs") q(".br-favs").click();
  else if (kind === "favitem") q(".fav-item").click();
};
T.actRobot = async (mistakes) => {
  const q = (s) => document.querySelector(s), need = q("#screen").dataset.need;
  if (q(".rrun") && need) {
    const clear = () => { for (let i = 0; i < 12 && q(".rslot.filled"); i++) q(".rundo").click(); };
    clear();
    if (mistakes && !T.actRobot.failed) {                                 // a wrong program: the robot walks back, nothing is lost
      T.actRobot.failed = true;
      q('.rcard[data-card="U"]').click(); q(".rrun").click();
      await T.wait(2500);                                                 // one step, then it walks back
      T.check("after a wrong program the robot is back at the start and the program is kept", !!q(".rslot.filled") && q("#screen").dataset.need === need);
      clear();
    }
    for (const card of need.split(",")) q(`.rcard[data-card="${card}"]`).click();
    q(".rrun").click();
    await T.until(() => T.name() === "celebrate" || !q(".rrun"), 20000);
  }
};
T.act.resetEveryday = () => { T.actPaint.wrongColour = false; T.actDesktop.missed = false; T.actDesktop.slow = false; T.actDesktop.wrongTap = false; T.actInternet.wobbled = false; T.actRobot.failed = false; };
})();
