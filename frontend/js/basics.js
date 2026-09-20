// Computer Basics Cove: six tiny lessons. Every lesson is pictures plus a spoken
// sentence. Nothing can be failed: a wrong choice just wobbles, the right
// answer pulses, and Tippy says "try another one".

const BASICS_ICONS = ["🖥️", "🪟", "📁", "⏰", "🙋", "🤐"];

function computerCove() {
  levelPicker("basics", "🐚", BASICS_ICONS, (n) => {
    [lessonParts, lessonWindow, lessonFolders, lessonBreak, lessonAsk, lessonSecrets,
      lessonInternet, lessonSave, lessonKind, lessonPad, lessonEmergency, lessonTraffic,
      lessonFlags, lessonAnimalHomes, lessonFood, lessonWeather][n - 1](
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
  queueMicrotask(() => speak(text));   // after the screen is set: setScreen() silences the previous screen
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

// ---------- Bonus 7. What is the internet? ----------
function lessonInternet(done) {
  chooseSteps("basics-7", [
    { icon: "🌐", prompt: t("b7.wifi"), options: [{ emoji: "📶" }, { emoji: "📺" }, { emoji: "🔦" }], answer: 0, fact: t("b7.wifi.fact") },
    { icon: "🌐", prompt: t("b7.ask"), scene: "🦒 ❓", options: [{ emoji: "🌍🔍" }, { emoji: "🍎" }, { emoji: "⚽" }], answer: 0, fact: t("b7.ask.fact") },
  ], done);
}

// ---------- Bonus 8. Saving a picture ----------
function lessonSave(done) {
  chooseSteps("basics-8", [
    { icon: "💾", prompt: t("b8.save"), scene: "🖼️", options: [{ emoji: "💾" }, { emoji: "🗑️" }, { emoji: "🔦" }], answer: 0, fact: t("b8.save.fact") },
    { icon: "📁", prompt: t("b8.where"), scene: "💾 ➡️", options: [{ emoji: "📁" }, { emoji: "🍽️" }, { emoji: "🪣" }], answer: 0, fact: t("b8.where.fact") },
  ], done);
}

// ---------- Bonus 9. Being kind online ----------
function lessonKind(done) {
  chooseSteps("basics-9", [
    { icon: "💛", prompt: t("b9.sad"), scene: "😢", options: [{ emoji: "💛" }, { emoji: "😠" }], answer: 0 },
    { icon: "🙋", prompt: t("b9.mean"), scene: "😠 💬", options: [{ emoji: "🙋" }, { emoji: "😠" }], answer: 0, fact: t("b9.fact") },
  ], done);
}

// ---------- Bonus 10. The touchpad ----------
function lessonPad(done) {
  chooseSteps("basics-10", [
    { icon: "☝️", prompt: t("b10.move"), scene: "➡️ 🖱️", options: [{ emoji: "☝️" }, { emoji: "🖐️" }, { emoji: "🦶" }], answer: 0, fact: t("b10.move.fact") },
    { icon: "👇", prompt: t("b10.click"), options: [{ emoji: "👇" }, { emoji: "🖐️" }], answer: 0 },
    { icon: "✌️", prompt: t("b10.scroll"), scene: "⬆️ ⬇️", options: [{ emoji: "✌️" }, { emoji: "☝️" }, { emoji: "🖐️" }], answer: 0, fact: t("b10.fact") },
  ], done);
}

// ---------- Bonus 11 (German). The emergency number ----------
// In Germany the fire brigade and the ambulance are reached on 112, the police on 110. A grown-up calls.
function lessonEmergency(done) {
  const services = [{ emoji: "🚒" }, { emoji: "🚑" }, { emoji: "🚓" }];
  chooseSteps("basics-11", [
    { icon: "🚒", prompt: t("de.b11.fire"), scene: "🔥", options: services, answer: 0, fact: t("de.b11.fire.fact") },
    { icon: "🚑", prompt: t("de.b11.hurt"), scene: "🤕", options: services, answer: 1, fact: t("de.b11.hurt.fact") },
    { icon: "🚓", prompt: t("de.b11.thief"), scene: "🦹", options: services, answer: 2, fact: t("de.b11.thief.fact") },
  ], done);
}

// ---------- Bonus 12 (German). Traffic lights and the zebra crossing ----------
function lessonTraffic(done) {
  chooseSteps("basics-12", [
    { icon: "🔴", prompt: t("de.b12.red"), scene: "🚦 🔴", options: [{ emoji: "✋" }, { emoji: "🚶" }], answer: 0, fact: t("de.b12.red.fact") },
    { icon: "🟢", prompt: t("de.b12.green"), scene: "🚦 🟢", options: [{ emoji: "👀" }, { emoji: "🏃" }], answer: 0, fact: t("de.b12.green.fact") },
    { icon: "🦓", prompt: t("de.b12.cross"), scene: "🛣️", options: [{ emoji: "🦓" }, { emoji: "🏃" }, { emoji: "🚗" }], answer: 0, fact: t("de.b12.cross.fact") },
  ], done);
}

// ---------- Bonus 13. Flags of the world ----------
function lessonFlags(done) {
  chooseSteps("basics-13", [
    { icon: "🇯🇵", prompt: t("b13.japan"), options: [{ emoji: "🇯🇵" }, { emoji: "🇧🇷" }, { emoji: "🇮🇹" }], answer: 0, fact: t("b13.japan.fact") },
    { icon: "🇧🇷", prompt: t("b13.brazil"), options: [{ emoji: "🇧🇷" }, { emoji: "🇪🇸" }, { emoji: "🇫🇷" }], answer: 0, fact: t("b13.brazil.fact") },
    { icon: "🇩🇪", prompt: t("b13.germany"), options: [{ emoji: "🇩🇪" }, { emoji: "🇨🇦" }, { emoji: "🇬🇷" }], answer: 0, fact: t("b13.germany.fact") },
  ], done);
}

// ---------- Bonus 14. Where animals live ----------
function lessonAnimalHomes(done) {
  chooseSteps("basics-14", [
    { icon: "🐟", prompt: t("b14.fish"), scene: "🐟", options: [{ emoji: "🌊" }, { emoji: "🏜️" }, { emoji: "❄️" }], answer: 0, fact: t("b14.fish.fact") },
    { icon: "🐦", prompt: t("b14.bird"), scene: "🐦", options: [{ emoji: "🪺" }, { emoji: "🌊" }, { emoji: "🏜️" }], answer: 0, fact: t("b14.bird.fact") },
    { icon: "🐪", prompt: t("b14.camel"), scene: "🐪", options: [{ emoji: "🏜️" }, { emoji: "🌊" }, { emoji: "❄️" }], answer: 0, fact: t("b14.camel.fact") },
  ], done);
}

// ---------- Bonus 15. Good food ----------
function lessonFood(done) {
  chooseSteps("basics-15", [
    { icon: "🍎", prompt: t("b15.fruit"), options: [{ emoji: "🍎" }, { emoji: "🍰" }, { emoji: "🍟" }], answer: 0, fact: t("b15.fruit.fact") },
    { icon: "🥕", prompt: t("b15.veg"), options: [{ emoji: "🥕" }, { emoji: "🍭" }, { emoji: "🍩" }], answer: 0, fact: t("b15.veg.fact") },
    { icon: "💧", prompt: t("b15.water"), options: [{ emoji: "💧" }, { emoji: "🥤" }, { emoji: "🍬" }], answer: 0, fact: t("b15.water.fact") },
  ], done);
}

// ---------- Bonus 16. Weather ----------
function lessonWeather(done) {
  const gear = [{ emoji: "☔" }, { emoji: "🕶️" }, { emoji: "🧤" }];
  chooseSteps("basics-16", [
    { icon: "🌧️", prompt: t("b16.rain"), scene: "🌧️", options: gear, answer: 0, fact: t("b16.rain.fact") },
    { icon: "☀️", prompt: t("b16.sun"), scene: "☀️", options: gear, answer: 1, fact: t("b16.sun.fact") },
    { icon: "❄️", prompt: t("b16.snow"), scene: "❄️", options: gear, answer: 2, fact: t("b16.snow.fact") },
  ], done);
}
