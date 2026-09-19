// Tippy frontend. Plain JavaScript, no build step.
// Sections: helpers, sound and voice, mascot, screens, parent area, start-up.

// ---------- Helpers ----------
const $ = (sel) => document.querySelector(sel);
let settings = { language: "en", keyboard_layout: "qwerty", voice_on: true, sound_on: true, child_name: "", favorite_word: "" };
// The languages Tippy speaks: [{code, native, voice, keyboard}], loaded from the server at start-up.
let LANGUAGES = [{ code: "en", native: "English", voice: "en-US", keyboard: "qwerty" }];
const languageOptions = () => LANGUAGES.map((l) => [l.code, l.native]);

let muted = false; // the child's quick mute button; lasts until the app is closed
let parentToken = null; // set after the correct PIN, kept only in memory
// The game that is running sets this to receive key presses. It is cleared
// whenever the screen changes, so a finished game can never react to keys.
let keyHandler = null;

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

// One musical note. "bell" adds a shimmering overtone (like a xylophone),
// "glide" slides the pitch up or down (springy, cartoon-like sounds).
// Every note fades in and out quickly: abrupt starts and stops cause clicks.
function tone(freq, when, dur, { gain = 0.12, bell = true, glideTo = null } = {}) {
  const start = audio.currentTime + when;
  const partials = bell ? [[1, 1], [2.76, 0.25], [5.4, 0.08]] : [[1, 1]];
  for (const [ratio, level] of partials) {
    const osc = audio.createOscillator();
    const amp = audio.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(freq * ratio, start);
    if (glideTo) osc.frequency.exponentialRampToValueAtTime(glideTo * ratio, start + dur);
    amp.gain.setValueAtTime(0.0001, start);
    amp.gain.linearRampToValueAtTime(gain * level, start + 0.008);
    amp.gain.exponentialRampToValueAtTime(0.0001, start + dur);
    osc.connect(amp).connect(audio.destination);
    osc.start(start);
    osc.stop(start + dur + 0.02);
  }
}

// C major pentatonic: any mix of these notes sounds happy, never sour.
const C5 = 523.25, D5 = 587.33, E5 = 659.25, G5 = 783.99, A5 = 880, C6 = 1046.5, E6 = 1318.5;
const PENTATONIC = [C5, D5, E5, G5, A5, C6];

const SFX = {
  tap:     () => tone(PENTATONIC[Math.floor(Math.random() * PENTATONIC.length)], 0, 0.35),
  key:     () => tone(900, 0, 0.07, { bell: false, glideTo: 450, gain: 0.08 }),        // soft "pop"
  play:    () => [C5, E5, G5, C6].forEach((f, i) => tone(f, i * 0.08, 0.45)),          // going up!
  home:    () => [G5, E5, C5].forEach((f, i) => tone(f, i * 0.09, 0.4)),               // coming down
  boing:   () => { tone(260, 0, 0.32, { bell: false, glideTo: 620, gain: 0.14 });      // springy jump
                   tone(1200, 0.28, 0.15, { glideTo: 1800, gain: 0.06 }); },
  note:    (i) => tone(PENTATONIC[i % PENTATONIC.length] * (i >= PENTATONIC.length ? 2 : 1), 0, 0.3, { gain: 0.1 }), // step up the scale
  success: () => [C5, E5, G5, C6, E6].forEach((f, i) => tone(f, i * 0.09, 0.5)),       // for later worlds
  sparkle: () => [C6, E6, G5 * 2, C6 * 2].forEach((f, i) => tone(f, i * 0.06, 0.3, { gain: 0.07 })),
};

// Usage: sfx("tap"), or sfx("note", 3). Silent when the parent has turned sounds off.
function sfx(name, arg) {
  if (!settings.sound_on || muted) return;
  try {
    audio = audio || new AudioContext();
    if (audio.state === "suspended") audio.resume();
    SFX[name](arg);
  } catch (e) { /* no sound available: the app still works */ }
}

// Voices differ a lot between computers. macOS includes joke voices ("Zarvox",
// "Bubbles"...) and Chrome may pick a robotic online voice. We choose a natural one.
const NOVELTY_VOICES = /albert|bad news|bahh|bells|boing|bubbles|cellos|deranged|good news|hysterical|jester|organ|superstar|trinoids|whisper|wobble|zarvox|fred|junior|ralph|kathy|grandma|grandpa|rocko|flo|eddy|reed|sandy|shelley/i;
const NICE_VOICES = /samantha|ava|allison|susan|zoe|karen|moira|serena|daniel|anna|petra|marlene|helena|viktor|katja|hedda|amala|m[oó]nica|jorge|paulina|marisol|elvira|[aá]lvaro|lucia|laura|juan/i;

// `tag` is the voice we want, for example "es-ES" (Spanish as spoken in Spain). Any voice of the same
// language is fine, but one from the exact region wins.
function pickVoice(tag) {
  const language = tag.slice(0, 2).toLowerCase();
  const region = (v) => v.lang.replace("_", "-").toLowerCase();
  const voices = speechSynthesis.getVoices().filter((v) => region(v).startsWith(language));
  const score = (v) =>
    (region(v).startsWith(tag.toLowerCase()) ? 6 : 0) +
    (/premium|enhanced|natural/i.test(v.name) ? 8 : 0) +
    (NICE_VOICES.test(v.name) ? 4 : 0) +
    (v.localService ? 2 : 0) +         // computer's own voices; online ones can crackle or lag
    (/google/i.test(v.name) ? -1 : 0) -
    (NOVELTY_VOICES.test(v.name) ? 100 : 0);
  return voices.sort((a, b) => score(b) - score(a))[0] || null;
}

// The voice tag of the current language ("en-US", "de-DE", "es-ES"), from the server's language list.
function voiceTag() {
  const info = LANGUAGES.find((l) => l.code === settings.language);
  return info ? info.voice : "en-US";
}

function speak(text) {
  if (!settings.voice_on || muted || !("speechSynthesis" in window)) return;
  if (speechSynthesis.getVoices().length === 0) { // list not loaded yet: try again when it is
    speechSynthesis.addEventListener("voiceschanged", () => speak(text), { once: true });
    return;
  }
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const tag = voiceTag();
  u.lang = tag;
  const voice = pickVoice(tag);
  if (voice) u.voice = voice;
  u.rate = 0.95; // slightly slow; lower values make many voices sound robotic
  u.pitch = 1.1; // a touch brighter and friendlier for a child
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
    return (body.text || "").replaceAll("{child}", settings.child_name || t("friend"));
  } catch (e) {
    return "";
  }
}

// ---------- Screens ----------
function show(...nodes) {
  const screen = $("#screen");
  screen.replaceChildren(...nodes);
  $("#home-btn").hidden = nodes.length === 0 || ["welcome", "who"].includes(screen.dataset.name);
  updateWhoButton(screen.dataset.name);
}

// Every new screen gets a new number. A game that waits before moving on (a short pause after
// the last balloon, say) uses later() instead of setTimeout(): if the child pressed Home in the
// meantime, the screen number has changed and the pending step is quietly dropped. Without this,
// a "level finished" screen could pop up on top of the home screen.
let screenSerial = 0;
function later(fn, ms) {
  const serial = screenSerial;
  setTimeout(() => { if (serial === screenSerial) fn(); }, ms);
}

function setScreen(name, ...nodes) {
  screenSerial++;
  keyHandler = null;
  padOnlyScreen = false;
  delete $("#screen").dataset.answer;   // Number Land sets this so the tests know the right answer
  $("#screen").dataset.name = name;
  show(...nodes);
}

async function welcomeScreen() {
  const mascot = mascotSVG();
  const bubble = el("div", { class: "bubble" }, "…");
  const play = el("button", { class: "big-btn play-btn", onclick: () => { sfx("play"); mapScreen(); } }, "▶ " + t("play"));
  setScreen("welcome", el("h1", { class: "title" }, window.TIPPY_CONFIG.mascotName), mascot, bubble, play);
  const line = await mascotLine("welcome");
  bubble.textContent = line;
  // Tapping the mascot repeats the line aloud and makes it jump.
  mascot.addEventListener("click", () => {
    mascot.classList.remove("jump"); void mascot.offsetWidth; mascot.classList.add("jump");
    sfx("boing"); speak(bubble.textContent);
  });
  speak(line);
}

const WORLDS = [
  ["mouse", "🐭"], ["keyboard", "⌨️"], ["letters", "🔤"], ["numbers", "🔢"], ["words", "🌳"],
  ["sentences", "☁️"], ["basics", "🖥️"], ["free", "🎨"],
];

async function mapScreen() {
  await loadProgress();
  const grid = el("div", { class: "worlds" });
  for (const [id, icon] of WORLDS) {
    const info = progress.worlds[id];
    const label = t("world." + id) + (info.complete ? " ✅" : "");
    grid.append(el("button", { class: "world" + (info.unlocked ? "" : " locked"), onclick: () => openWorld(id) },
      el("span", { class: "icon" }, info.unlocked ? icon : "🔒"), label));
  }
  const chips = el("div", { class: "map-top" },
    el("span", { class: "chip" }, `⭐ ${progress.total_stars}`),
    el("button", { class: "chip", onclick: () => { sfx("tap"); albumScreen(); } }, `📖 ${progress.stickers.length}`));
  if (progress.streak >= 2) chips.append(el("span", { class: "chip" }, `🔥 ${progress.streak}`));
  if (settings.ask_tippy) chips.append(el("button", { class: "chip", onclick: () => { sfx("tap"); askTippy(); } }, "💬 " + t("ask.chip")));
  setScreen("map", chips, el("div", { class: "bubble" }, t("chooseWorld")), grid);
  speak(t("chooseWorld"));
}

function openWorld(id) {
  if (!progress.worlds[id].unlocked) { sfx("key"); speak(t("lockedWorld")); return; }
  sfx("tap");
  if (id === "mouse") mouseMeadow();
  else if (id === "keyboard") kingdom();
  else if (id === "letters") letterLand();
  else if (id === "numbers") numberLand();
  else if (id === "words") wordWoods();
  else if (id === "sentences") sentenceSky();
  else if (id === "basics") computerCove();
  else if (id === "free") freePlay();
  else comingSoonScreen(id);
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
function closeModal() {
  $("#modal-root").replaceChildren();
  if (limitReached) showLimit(); // the daily limit screen comes back when a parent screen is closed
}
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
    entered += d; refresh(); sfx("key");
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

// A text box for the parent (name, favourite word). Saved when the parent leaves the box.
// These stay on this computer: they are used to show the child their own name and are never sent to the LLM.
function textRow(label, key, value, maxLength) {
  const input = el("input", { class: "text-input", type: "text", maxlength: String(maxLength), value: value || "",
    onchange: () => saveSetting({ [key]: input.value.trim() }) });
  return el("div", { class: "row" }, el("span", {}, label), input);
}

// Language, text size and reduced motion are applied to the page here.
function applyLook() {
  document.documentElement.lang = settings.language;
  document.documentElement.style.setProperty("--font-scale", settings.font_scale || 1);
  document.body.classList.toggle("reduce-motion", !!settings.reduce_motion);
}

async function saveSetting(patch) {
  const { status, body } = await api("/api/parent/settings", { method: "POST", body: JSON.stringify(patch) });
  if (status === 200) settings = { ...settings, ...body }; // a refused value just shows the old one again
  applyLook();
  parentPanel();
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
    else if (e.key === "Escape" && !setupActive) closeModal();
    e.preventDefault();
    return;
  }
  const isShortcut = e.ctrlKey || e.metaKey || e.altKey;
  const isFunctionKey = /^F([1-9]|1[0-2])$/.test(e.key);
  // A game is running: it gets every normal key (and the browser gets none,
  // so Space does not scroll and Backspace does not go "back").
  if (keyHandler && !isShortcut && !isFunctionKey && e.key !== "Escape" && e.key !== "Tab"
      && $("#modal-root").children.length === 0) {
    e.preventDefault();
    if (!e.repeat) keyHandler(e); // holding a key down counts once
    return;
  }
  if (isShortcut || isFunctionKey || e.key === "Escape" || e.key === "Tab") e.preventDefault();
}, true);
document.addEventListener("contextmenu", (e) => e.preventDefault());

// ---------- Start-up ----------
$("#home-btn").addEventListener("click", () => { sfx("home"); welcomeScreen(); });
$("#mute-btn").addEventListener("click", () => {
  muted = !muted;
  if (muted && "speechSynthesis" in window) speechSynthesis.cancel();
  $("#mute-btn").textContent = muted ? "🔇" : "🔊";
  sfx("tap");
});
$("#who-btn").addEventListener("click", () => { sfx("tap"); whoIsPlaying(); });
$("#parent-btn").addEventListener("click", () => openModal(pinPad()));

(async function start() {
  try {
    const { body } = await api("/api/settings");
    settings = { ...settings, ...body };
    const languages = await api("/api/languages");
    if (languages.status === 200) LANGUAGES = languages.body.languages;
    applyLook();
    api("/api/visit", { method: "POST" }); // counts today for the streak
    if (settings.setup_needed) { await welcomeScreen(); setupWizard(); return; }
    const several = settings.profile_count > 1;
    startLimits(!several);            // with several children the limits are checked once one is chosen
    if (several) await whoIsPlaying(); else await welcomeScreen();
  } catch (e) {
    errorScreen(e);
  }
})();
