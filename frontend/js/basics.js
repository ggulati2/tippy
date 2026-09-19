// Computer Basics Cove: six tiny lessons. Every lesson is pictures plus a spoken
// sentence. Nothing can be failed: a wrong choice just wobbles, the right
// answer pulses, and Tippy says "try another one".

const BASICS_ICONS = ["🖥️", "🪟", "📁", "⏰", "🙋", "🤐"];

function computerCove() {
  levelPicker("basics", "🐚", BASICS_ICONS, (n) => {
    [lessonParts, lessonWindow, lessonFolders, lessonBreak, lessonAsk, lessonSecrets][n - 1](
      () => completeLevel("basics", n, computerCove));
  });
}

const shuffled = (list) => {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
};

// A speech bubble whose words can change during a lesson (tap it to hear it again).
function liveInstruction(icon, text) {
  let spoken = text;
  const node = el("button", { class: "bubble instruction", onclick: () => speak(spoken) }, `${icon} ${text} 🔊`);
  speak(text);
  return { node, set(newIcon, newText) { spoken = newText; node.textContent = `${newIcon} ${newText} 🔊`; speak(newText); } };
}

// The engine behind most lessons: show a picture and a few big choices.
// steps: [{ icon, prompt, scene, options: [{ emoji }], answer: index, fact }]
function chooseSteps(screen, steps, done) {
  let index = 0;
  const dots = progressDots(0, steps.length);
  const bubble = liveInstruction(steps[0].icon, steps[0].prompt);
  const sceneBox = el("div", { class: "scene-card" });
  const choices = el("div", { class: "choices" });
  setScreen(screen, bubble.node, sceneBox, choices, dots);

  function show() {
    const step = steps[index];
    if (index > 0) bubble.set(step.icon, step.prompt); // the first prompt is already spoken
    sceneBox.textContent = step.scene || "";
    sceneBox.hidden = !step.scene;
    const order = shuffled(step.options.map((option, i) => ({ ...option, right: i === step.answer })));
    choices.replaceChildren(...order.map((option) => {
      const card = el("button", { class: "choice" }, option.emoji);
      card.addEventListener("click", () => pick(card, option));
      return card;
    }));
  }

  function pick(card, option) {
    const step = steps[index];
    if (!option.right) {
      // Wrong choice: no buzzer, no red. Wobble, then point at the right one.
      replayAnimation(card, "wobble");
      sfx("key");
      const right = [...choices.children].find((c) => c.textContent === step.options[step.answer].emoji);
      replayAnimation(right, "attention");
      speak(t("basics.tryAgain"));
      return;
    }
    [...choices.children].forEach((c) => (c.disabled = true));
    card.classList.add("chosen");
    replayAnimation(card, "jump-up");
    sfx("success");
    dots.textContent = progressDots(index + 1, steps.length).textContent;
    if (step.fact) speak(step.fact);
    later(() => {
      index++;
      if (index === steps.length) done(); else show();
    }, step.fact ? 2600 : 1200);
  }
  show();
}

// ---------- 1. Screen, mouse, keyboard ----------
function lessonParts(done) {
  const options = [{ emoji: "🖥️" }, { emoji: "🖱️" }, { emoji: "⌨️" }];
  chooseSteps("basics-1", [
    { icon: "🖥️", prompt: t("b1.screen"), options, answer: 0, fact: t("b1.screen.fact") },
    { icon: "🖱️", prompt: t("b1.mouse"), options, answer: 1, fact: t("b1.mouse.fact") },
    { icon: "⌨️", prompt: t("b1.keyboard"), options, answer: 2, fact: t("b1.keyboard.fact") },
  ], done);
}

// ---------- 2. Open and close a window ----------
function lessonWindow(done) {
  const total = 2;
  let count = 0;
  const bubble = liveInstruction("🪟", t("b2.open"));
  const desk = el("div", { class: "desktop" });
  const dots = progressDots(0, total);
  setScreen("basics-2", bubble.node, desk, dots);

  function showIcon() {
    if (count > 0) bubble.set("🪟", t("b2.open")); // the first time it is already spoken
    const icon = el("button", { class: "app-icon", onclick: openWindow }, el("span", { class: "app-emoji" }, "🎨"));
    desk.replaceChildren(icon);
  }

  function openWindow() {
    sfx("boing");
    bubble.set("❌", t("b2.close"));
    const close = el("button", { class: "close-x", "aria-label": "close", onclick: () => closeWindow(win) }, "✖");
    const win = el("div", { class: "fake-window opening" },
      el("div", { class: "title-bar" }, el("span", {}, "🎨"), close), el("div", { class: "win-body" }, "😀"));
    desk.replaceChildren(win);
  }

  function closeWindow(win) {
    if (win.classList.contains("closing")) return; // a double-click on ✖ must count once
    win.classList.add("closing");
    sfx("tap");
    count++;
    dots.textContent = progressDots(count, total).textContent;
    if (count === total) { speak(t("b2.fact")); return later(done, 2200); }
    later(showIcon, 500);
  }
  showIcon();
}

// ---------- 3. Files and folders ----------
function lessonFolders(done) {
  const folders = [{ emoji: "📁🖼️" }, { emoji: "📁🎵" }, { emoji: "📁📝" }];
  chooseSteps("basics-3", [
    { icon: "📁", prompt: t("b3.ask"), scene: "📷", options: folders, answer: 0 },
    { icon: "📁", prompt: t("b3.ask"), scene: "🎵", options: folders, answer: 1 },
    { icon: "📁", prompt: t("b3.ask"), scene: "📝", options: folders, answer: 2, fact: t("b3.fact") },
  ], done);
}

// ---------- 4. Screen breaks ----------
function lessonBreak(done) {
  chooseSteps("basics-4", [
    { icon: "⏰", prompt: t("b4.look"), scene: "🌳⛰️☁️", options: [{ emoji: "👀" }], answer: 0 },
    { icon: "⏰", prompt: t("b4.stretch"), scene: "🙆", options: [{ emoji: "🤸" }], answer: 0 },
    { icon: "⏰", prompt: t("b4.drink"), scene: "💧", options: [{ emoji: "🥤" }], answer: 0, fact: t("b4.fact") },
  ], done);
}

// ---------- 5. Ask a grown-up first ----------
function lessonAsk(done) {
  const options = [{ emoji: "🙋" }, { emoji: "🖱️" }];   // 🙋 = ask a grown-up, 🖱️ = just click
  const step = (scene, fact) => ({ icon: "🙋", prompt: t("b5.ask"), scene, options, answer: 0, fact });
  chooseSteps("basics-5", [step("🎁 ✨ 🎉"), step("🔗 ❓"), step("📦 ⬇️ ❓", t("b5.fact"))], done);
}

// ---------- 6. Keep private things secret online ----------
function lessonSecrets(done) {
  const options = [{ emoji: "🤐" }, { emoji: "💬" }];   // 🤐 = keep it secret, 💬 = tell
  chooseSteps("basics-6", [
    { icon: "🤐", prompt: t("b6.address"), scene: "🏠 ❓", options, answer: 0 },
    { icon: "🤐", prompt: t("b6.name"), scene: "🧒 ❓", options, answer: 0 },
    { icon: "🤐", prompt: t("b6.password"), scene: "🔑 ❓", options, answer: 0, fact: t("b6.fact") },
  ], done);
}
