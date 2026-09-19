// Mouse Meadow: four tiny games that teach pointing, clicking, dragging,
// double-clicking and scrolling. No timers, no lives: mistakes only get a
// friendly hint, and every game ends with a celebration.

const MOUSE_LEVELS = [
  { icon: "🎈", text: "mouse.pop", run: levelPop },
  { icon: "🧺", text: "mouse.drag", run: levelDrag },
  { icon: "🥚", text: "mouse.dbl", run: levelDoubleClick },
  { icon: "📜", text: "mouse.scroll", run: levelScroll },
];

const rand = (min, max) => min + Math.random() * (max - min);

// The instruction at the top of a game: an icon, a short line, and a 🔊 to hear it again.
function instruction(icon, text) {
  const bubble = el("button", { class: "bubble instruction", onclick: () => speak(text) }, `${icon} ${text} 🔊`);
  speak(text);
  return bubble;
}

// A row of dots showing how far along the game is.
function progressDots(done, total) {
  return el("div", { class: "dots" }, "●".repeat(Math.min(done, total)) + "○".repeat(Math.max(0, total - done)));
}

// ---------- Level picker ----------
async function mouseMeadow() {
  await loadProgress();
  const stars = progress.worlds.mouse.levels;
  const cards = MOUSE_LEVELS.map((level, i) => {
    const n = i + 1;
    const earned = stars[n] || 0;
    return el("button", { class: "world level", onclick: () => { sfx("tap"); startMouseLevel(n); } },
      el("span", { class: "icon" }, level.icon),
      el("span", { class: "stars" }, earned ? "⭐".repeat(earned) : "☆☆☆"));
  });
  setScreen("mouse", el("h1", { class: "title" }, "🐭 " + t("world.mouse")), el("div", { class: "worlds" }, ...cards));
  speak(t("world.mouse"));
}

function startMouseLevel(n) {
  const level = MOUSE_LEVELS[n - 1];
  level.run(() => completeLevel("mouse", n, mouseMeadow));
}

// ---------- Level 1: move and click ----------
// One big balloon at a time: easiest possible target.
function levelPop(done) {
  const total = 5;
  let popped = 0;
  const arena = el("div", { class: "arena" });
  const dots = progressDots(0, total);
  setScreen("mouse-1", instruction("🎈", t("mouse.pop")), dots, arena);

  function spawn() {
    const balloon = el("button", { class: "target balloon", "aria-label": "balloon" }, "🎈");
    // Anywhere in the play area, but always fully inside it (the balloon is 150px wide and tall).
    balloon.style.left = `calc((100% - 150px) * ${rand(0.03, 0.97)})`;
    balloon.style.top = `calc((100% - 150px) * ${rand(0.03, 0.97)})`;
    balloon.style.filter = `hue-rotate(${Math.floor(rand(0, 360))}deg)`;
    balloon.addEventListener("click", () => {
      sfx("tap");
      balloon.classList.add("pop");
      popped++;
      dots.textContent = progressDots(popped, total).textContent;
      later(() => (popped === total ? done() : spawn()), 350);
      balloon.disabled = true;
    });
    arena.replaceChildren(balloon);
  }
  spawn();
}

// ---------- Level 2: drag and drop ----------
function levelDrag(done) {
  const shapes = [
    { name: "circle", color: "#ff6b6b" },
    { name: "square", color: "#4dabf7" },
    { name: "triangle", color: "#fcc419" },
  ];
  const shuffled = [...shapes].sort(() => Math.random() - 0.5);
  const tray = el("div", { class: "tray" });
  const baskets = el("div", { class: "tray baskets" });
  let placed = 0;
  const dots = progressDots(0, shapes.length);
  const bubble = instruction("🧺", t("mouse.drag"));

  const shapeEl = (s, cls) => {
    const node = el("div", { class: `shape ${s.name} ${cls}` });
    node.style.setProperty("--c", s.color);
    node.dataset.shape = s.name;
    return node;
  };

  for (const s of shapes) {
    const basket = el("div", { class: "basket", "data-shape": s.name }, shapeEl(s, "ghost"));
    basket.style.borderColor = s.color;
    baskets.append(basket);
  }

  for (const s of shuffled) {
    const item = shapeEl(s, "draggable");
    let startX = 0, startY = 0;
    item.addEventListener("pointerdown", (e) => {
      item.setPointerCapture(e.pointerId);
      startX = e.clientX; startY = e.clientY;
      item.classList.add("dragging");
      item.style.transition = "none";
      sfx("key");
    });
    item.addEventListener("pointermove", (e) => {
      if (!item.classList.contains("dragging")) return;
      item.style.transform = `translate(${e.clientX - startX}px, ${e.clientY - startY}px)`;
    });
    item.addEventListener("pointerup", (e) => {
      if (!item.classList.contains("dragging")) return;
      item.classList.remove("dragging");
      const basket = document.elementsFromPoint(e.clientX, e.clientY).find((n) => n.classList?.contains("basket"));
      if (basket && basket.dataset.shape === s.name) {
        // Right basket: it drops in and stays there.
        item.style.transform = "";
        item.classList.remove("draggable");
        item.style.pointerEvents = "none";
        basket.replaceChildren(item);
        sfx("success");
        placed++;
        dots.textContent = progressDots(placed, shapes.length).textContent;
        if (placed === shapes.length) later(done, 700);
        return;
      }
      // Wrong basket, or dropped elsewhere: glide home and point at the right basket. No buzzer.
      item.style.transition = "transform .35s ease";
      item.style.transform = "";
      const right = baskets.querySelector(`[data-shape="${s.name}"]`);
      right.classList.add("hint");
      setTimeout(() => right.classList.remove("hint"), 1800);
      if (basket) speak(t("mouse.tryBasket"));
    });
    tray.append(item);
  }
  setScreen("mouse-2", bubble, dots, tray, baskets);
}

// ---------- Level 3: double-click ----------
function levelDoubleClick(done) {
  const hatchlings = ["🐥", "🦖", "🐢"];
  let hatched = 0;
  const arena = el("div", { class: "arena center" });
  const dots = progressDots(0, hatchlings.length);
  setScreen("mouse-3", instruction("🥚", t("mouse.dbl")), dots, arena);

  function nextEgg() {
    const egg = el("button", { class: "target egg", "aria-label": "egg" }, "🥚");
    const hint = el("div", { class: "double-hint" }, "👆👆");
    // A single click only wiggles the egg and shows the hint again. Nothing bad happens.
    egg.addEventListener("click", () => {
      egg.classList.remove("wobble"); void egg.offsetWidth; egg.classList.add("wobble");
      sfx("key");
    });
    egg.addEventListener("dblclick", () => {
      egg.disabled = true;
      egg.textContent = hatchlings[hatched];
      egg.classList.add("hatched");
      hint.remove();
      sfx("boing");
      hatched++;
      dots.textContent = progressDots(hatched, hatchlings.length).textContent;
      later(() => (hatched === hatchlings.length ? done() : nextEgg()), 1100);
    });
    arena.replaceChildren(egg, hint);
  }
  nextEgg();
}

// ---------- Level 4: scroll ----------
function levelScroll(done) {
  const scroller = el("div", { class: "scroller" });
  const tall = el("div", { class: "tall" });
  const decorations = ["🌳", "🌼", "☁️", "🦋", "🌷", "🐝", "🌲", "🍄"];
  for (let i = 0; i < 26; i++) {
    const d = el("span", { class: "deco" }, decorations[i % decorations.length]);
    d.style.left = rand(3, 90) + "%";
    d.style.top = rand(12, 88) + "%";
    tall.append(d);
  }
  tall.append(el("div", { class: "scroll-hint" }, "⬇️"));
  const chest = el("button", { class: "target chest", "aria-label": "treasure" }, "🎁");
  chest.addEventListener("click", () => { chest.disabled = true; sfx("boing"); later(done, 700); });
  tall.append(chest);
  scroller.append(tall);
  setScreen("mouse-4", instruction("📜", t("mouse.scroll")), scroller);
}
