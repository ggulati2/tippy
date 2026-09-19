// Tippy frontend. Plain JavaScript, no build step.
// Sections: helpers, sound and voice, mascot, screens, parent area, start-up.

// ---------- Helpers ----------
const $ = (sel) => document.querySelector(sel);
let settings = { language: "en", keyboard_layout: "qwerty", voice_on: true, sound_on: true };
let parentToken = null; // set after the correct PIN, kept only in memory

const t = (key) => (STRINGS[settings.language] || STRINGS.en)[key] || STRINGS.en[key] || key;

// Build an element. Text is always added with textContent, never as HTML,
// so text from the LLM can never inject markup.
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const c of children) node.append(c);
  return node;
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json" };
  if (parentToken) headers["X-Parent-Token"] = parentToken;
  const res = await fetch(path, { ...options, headers });
  const body = await res.json().catch(() => ({}));
  return { status: res.status, body };
}

// ---------- Sound and voice ----------
let audio = null;
function beep(freq = 660, ms = 120) {
  if (!settings.sound_on) return;
  try {
    audio = audio || new AudioContext();
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    const now = audio.currentTime;
    const end = now + ms / 1000;
    osc.type = "sine"; // the softest tone: no harsh buzz
    osc.frequency.value = freq;
    // Fade in and out quickly. Starting or stopping a tone abruptly makes
    // a "click" that sounds like a broken speaker.
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.linearRampToValueAtTime(0.06, now + 0.01);
    gain.gain.linearRampToValueAtTime(0.0001, end);
    osc.connect(gain).connect(audio.destination);
    osc.start(now);
    osc.stop(end + 0.02);
  } catch (e) { /* no sound available: the app still works */ }
}

// Voices differ a lot between computers. macOS includes joke voices ("Zarvox",
// "Bubbles"...) and Chrome may pick a robotic online voice. We choose a natural one.
const NOVELTY_VOICES = /albert|bad news|bahh|bells|boing|bubbles|cellos|deranged|good news|hysterical|jester|organ|superstar|trinoids|whisper|wobble|zarvox|fred|junior|ralph|kathy|grandma|grandpa|rocko|flo|eddy|reed|sandy|shelley/i;
const NICE_VOICES = /samantha|ava|allison|susan|zoe|karen|moira|serena|daniel|anna|petra|marlene|helena|viktor|katja|hedda|amala/i;

function pickVoice(lang) {
  const voices = speechSynthesis.getVoices().filter((v) => v.lang.replace("_", "-").toLowerCase().startsWith(lang));
  const score = (v) =>
    (/premium|enhanced|natural/i.test(v.name) ? 8 : 0) +
    (NICE_VOICES.test(v.name) ? 4 : 0) +
    (v.localService ? 2 : 0) +         // computer's own voices; online ones can crackle or lag
    (/google/i.test(v.name) ? -1 : 0) -
    (NOVELTY_VOICES.test(v.name) ? 100 : 0);
  return voices.sort((a, b) => score(b) - score(a))[0] || null;
}

function speak(text) {
  if (!settings.voice_on || !("speechSynthesis" in window)) return;
  if (speechSynthesis.getVoices().length === 0) { // list not loaded yet: try again when it is
    speechSynthesis.addEventListener("voiceschanged", () => speak(text), { once: true });
    return;
  }
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const lang = settings.language === "de" ? "de" : "en";
  u.lang = lang === "de" ? "de-DE" : "en-US";
  const voice = pickVoice(lang);
  if (voice) u.voice = voice;
  u.rate = 0.95; // slightly slow; lower values make many voices sound robotic
  speechSynthesis.speak(u);
}
// The voice list loads a moment after the page opens; touching it early wakes it up.
if ("speechSynthesis" in window) speechSynthesis.getVoices();

// ---------- Mascot ----------
function mascotSVG() {
  const c = window.TIPPY_CONFIG;
  const svg = `
  <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${c.mascotName}">
    <polygon points="45,70 35,15 85,45" fill="${c.mascotColor}"/>
    <polygon points="155,70 165,15 115,45" fill="${c.mascotColor}"/>
    <polygon points="48,60 43,30 68,48" fill="${c.mascotBellyColor}"/>
    <polygon points="152,60 157,30 132,48" fill="${c.mascotBellyColor}"/>
    <ellipse cx="100" cy="115" rx="80" ry="72" fill="${c.mascotColor}"/>
    <ellipse cx="100" cy="140" rx="48" ry="36" fill="${c.mascotBellyColor}"/>
    <ellipse class="eye" cx="70" cy="100" rx="11" ry="15" fill="#23395b"/>
    <ellipse class="eye" cx="130" cy="100" rx="11" ry="15" fill="#23395b"/>
    <circle cx="74" cy="95" r="4" fill="#fff"/><circle cx="134" cy="95" r="4" fill="#fff"/>
    <ellipse cx="100" cy="125" rx="9" ry="6" fill="#23395b"/>
    <path d="M84 138 Q100 156 116 138" stroke="#23395b" stroke-width="5" fill="none" stroke-linecap="round"/>
    <circle cx="52" cy="128" r="10" fill="#ff8787" opacity=".5"/>
    <circle cx="148" cy="128" r="10" fill="#ff8787" opacity=".5"/>
  </svg>`;
  const wrapper = el("div", { class: "mascot" });
  wrapper.innerHTML = svg; // our own fixed markup, not LLM text
  return wrapper;
}

// Ask the backend for a line and fill in the child's name locally.
// The name is never sent to the server, only substituted here.
async function mascotLine(event) {
  try {
    const { body } = await api(`/api/mascot/line?event=${encodeURIComponent(event)}`);
    return (body.text || "").replaceAll("{child}", t("friend"));
  } catch (e) {
    return "";
  }
}

// ---------- Screens ----------
function show(...nodes) {
  const screen = $("#screen");
  screen.replaceChildren(...nodes);
  $("#home-btn").hidden = nodes.length === 0 || screen.dataset.name === "welcome";
}

function setScreen(name, ...nodes) {
  $("#screen").dataset.name = name;
  show(...nodes);
}

async function welcomeScreen() {
  const mascot = mascotSVG();
  const bubble = el("div", { class: "bubble" }, "…");
  const play = el("button", { class: "big-btn play-btn", onclick: () => { beep(880); mapScreen(); } }, "▶ " + t("play"));
  setScreen("welcome", el("h1", { class: "title" }, window.TIPPY_CONFIG.mascotName), mascot, bubble, play);
  const line = await mascotLine("welcome");
  bubble.textContent = line;
  // Tapping the mascot repeats the line aloud and makes it jump.
  mascot.addEventListener("click", () => {
    mascot.classList.remove("jump"); void mascot.offsetWidth; mascot.classList.add("jump");
    beep(520); speak(bubble.textContent);
  });
  speak(line);
}

const WORLDS = [
  ["mouse", "🐭"], ["keyboard", "⌨️"], ["letters", "🔤"], ["words", "🌳"],
  ["sentences", "☁️"], ["basics", "🖥️"], ["free", "🎨"],
];

function mapScreen() {
  const grid = el("div", { class: "worlds" });
  for (const [id, icon] of WORLDS) {
    grid.append(el("button", { class: "world", onclick: () => { beep(700); comingSoonScreen(id); } },
      el("span", { class: "icon" }, icon), t("world." + id)));
  }
  setScreen("map", el("div", { class: "bubble" }, t("chooseWorld")), grid);
  speak(t("chooseWorld"));
}

function comingSoonScreen(worldId) {
  setScreen("soon", el("h1", { class: "title" }, t("world." + worldId)), mascotSVG(),
    el("div", { class: "bubble" }, t("comingSoonSay")));
  speak(t("comingSoonSay"));
}

// Shown for any unexpected problem. No technical words for the child.
function errorScreen(error) {
  console.error(error); // details for the parent; the child sees only the smile
  setScreen("error", el("div", { class: "oops" }, "😊"), el("h1", { class: "title" }, t("errorTitle")),
    el("button", { class: "big-btn", onclick: welcomeScreen }, "🏠"));
}
window.addEventListener("error", (e) => errorScreen(e.error));
window.addEventListener("unhandledrejection", (e) => errorScreen(e.reason));

// ---------- Parent area ----------
function closeModal() { $("#modal-root").replaceChildren(); }
function openModal(panel) {
  $("#modal-root").replaceChildren(el("div", { class: "overlay" }, panel));
}

function pinPad() {
  let entered = "";
  const dots = el("div", { class: "pin-dots" });
  const msg = el("div", { class: "pin-msg" });
  const refresh = () => { dots.textContent = "●".repeat(entered.length) || " "; };

  async function submit() {
    const { status, body } = await api("/api/parent/verify", { method: "POST", body: JSON.stringify({ pin: entered }) });
    entered = ""; refresh();
    if (body.ok) { parentToken = body.token; parentPanel(); return; }
    msg.textContent = status === 429 || body.locked_seconds ? t("locked") + ` (${body.locked_seconds}s)` : t("wrongPin");
  }
  function press(d) {
    if (entered.length >= 8) return;
    entered += d; refresh(); beep(500, 60);
  }

  const keys = "123456789".split("").map((d) => el("button", { onclick: () => press(d) }, d));
  keys.push(
    el("button", { onclick: () => { entered = entered.slice(0, -1); refresh(); } }, "⌫"),
    el("button", { onclick: () => press("0") }, "0"),
    el("button", { onclick: submit }, "✔"),
  );
  refresh();
  const panel = el("div", { class: "panel" },
    el("h2", {}, "🔒 " + t("enterPin")), dots, msg, el("div", { class: "keypad" }, ...keys),
    el("button", { class: "big-btn blue", onclick: closeModal }, t("back")));
  // Typing digits on the real keyboard works too (handled in keydown below).
  panel.pinPress = press; panel.pinSubmit = submit;
  panel.pinBack = () => { entered = entered.slice(0, -1); refresh(); };
  return panel;
}

function toggleRow(label, options, current, onPick) {
  const seg = el("div", { class: "seg" });
  for (const [value, text] of options) {
    seg.append(el("button", { class: String(value) === String(current) ? "on" : "", onclick: () => onPick(value) }, text));
  }
  return el("div", { class: "row" }, el("span", {}, label), seg);
}

async function saveSetting(patch) {
  const { body } = await api("/api/parent/settings", { method: "POST", body: JSON.stringify(patch) });
  settings = { ...settings, ...body };
  document.documentElement.lang = settings.language;
  parentPanel();
}

async function parentPanel() {
  const { body: status } = await api("/api/parent/status");
  const panel = el("div", { class: "panel" },
    el("h2", {}, "🔓 " + t("parentArea")),
    toggleRow(t("language"), [["en", "English"], ["de", "Deutsch"]], settings.language, (v) => saveSetting({ language: v })),
    toggleRow(t("keyboardLayout"), [["qwerty", "QWERTY"], ["qwertz", "QWERTZ"]], settings.keyboard_layout, (v) => saveSetting({ keyboard_layout: v })),
    toggleRow(t("voice"), [[true, t("on")], [false, t("off")]], settings.voice_on, (v) => saveSetting({ voice_on: v })),
    toggleRow(t("sound"), [[true, t("on")], [false, t("off")]], settings.sound_on, (v) => saveSetting({ sound_on: v })),
    el("div", { class: "row" }, el("span", {}, t("status")), el("span", {}, status.llm_mode === "live" ? t("llmLive") : t("llmMock"))),
    el("button", { class: "big-btn exit-btn", onclick: exitApp }, t("exitApp")),
    el("button", { class: "big-btn blue", onclick: () => { parentToken = null; closeModal(); welcomeScreen(); } }, t("back")));
  openModal(panel);
}

async function exitApp() {
  await api("/api/parent/exit", { method: "POST" });
  closeModal();
  setScreen("bye", mascotSVG(), el("h1", { class: "title" }, t("bye")));
  $("#parent-btn").hidden = true;
  speak(t("bye"));
  // The launcher closes the kiosk window; this is a backup for normal browsers.
  setTimeout(() => window.close(), 1500);
}

// ---------- Keyboard safety ----------
// Best effort: browsers do not allow blocking everything (for example Cmd+Q).
document.addEventListener("keydown", (e) => {
  const pad = document.querySelector(".keypad")?.closest(".panel");
  if (pad) { // the PIN pad is open: accept digits, Backspace, Enter
    if (/^[0-9]$/.test(e.key)) pad.pinPress(e.key);
    else if (e.key === "Backspace") pad.pinBack();
    else if (e.key === "Enter") pad.pinSubmit();
    else if (e.key === "Escape") closeModal();
    e.preventDefault();
    return;
  }
  const isShortcut = e.ctrlKey || e.metaKey || e.altKey;
  const isFunctionKey = /^F([1-9]|1[0-2])$/.test(e.key);
  if (isShortcut || isFunctionKey || e.key === "Escape" || e.key === "Tab") e.preventDefault();
}, true);
document.addEventListener("contextmenu", (e) => e.preventDefault());

// ---------- Start-up ----------
$("#home-btn").addEventListener("click", () => { beep(600); welcomeScreen(); });
$("#parent-btn").addEventListener("click", () => openModal(pinPad()));

(async function start() {
  try {
    const { body } = await api("/api/settings");
    settings = { ...settings, ...body };
    document.documentElement.lang = settings.language;
    await welcomeScreen();
  } catch (e) {
    errorScreen(e);
  }
})();
