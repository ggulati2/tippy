// Play-time limits.
//  - After the session length (default 10 minutes of active play) Tippy suggests a break.
//    It is a suggestion: the child can keep playing for 5 more minutes.
//  - At the daily limit (parent's choice, off by default) the game stops for today.
//    Only the parent can change that, from the parent area.
//
// Time only counts while the child is really playing: the window is visible,
// something was pressed in the last 30 seconds, and no parent screen is open.

let limitReached = false;
let sessionSeconds = 0;
let pendingSeconds = 0;
let lastActivity = Date.now();
let breakShown = false;
let limitShown = false;   // the goodnight screen is up
let limitPoll = 0;

const IDLE_AFTER_MS = 30000;
const HEARTBEAT_EVERY = 15;   // seconds of play between reports to the server
const SNOOZE_SECONDS = 300;   // "keep playing" gives 5 more minutes

for (const type of ["keydown", "pointerdown", "pointermove", "wheel"]) {
  document.addEventListener(type, () => { lastActivity = Date.now(); }, true);
}

function startLimits() {
  refreshLimits();
  setInterval(limitTick, 1000);
}

async function refreshLimits() {
  try {
    const { body } = await api("/api/limits");
    applyLimits(body);
  } catch (e) { /* no limits info: never block the child because of a technical problem */ }
}

function applyLimits(state) {
  settings.session_minutes = state.session_minutes;
  settings.daily_limit_minutes = state.daily_limit_minutes;
  limitReached = state.daily_reached;
  if (limitReached) showLimit();
  else if (limitShown) { // the limit no longer applies (a new day, or the parent raised it)
    limitShown = false;
    if (!parentToken) { closeModal(); welcomeScreen(); }
  }
}

function limitTick() {
  const modalOpen = $("#modal-root").children.length > 0;
  // While the goodnight screen is up, look every 30 seconds whether the limit still applies
  // (it stops applying at midnight), so Tippy is usable again without a restart.
  if (limitReached) { if (!parentToken && ++limitPoll % 30 === 0) refreshLimits(); return; }
  if (document.hidden || parentToken || modalOpen) return;
  if (Date.now() - lastActivity > IDLE_AFTER_MS) return; // walked away: not counted
  sessionSeconds++;
  pendingSeconds++;
  if (pendingSeconds >= HEARTBEAT_EVERY) reportPlayTime();
  if (settings.session_minutes > 0 && sessionSeconds >= settings.session_minutes * 60 && !breakShown) showBreak();
}

async function reportPlayTime() {
  const seconds = pendingSeconds;
  pendingSeconds = 0;
  try {
    const { status, body } = await api("/api/session/heartbeat", { method: "POST", body: JSON.stringify({ seconds }) });
    if (status === 200) applyLimits(body);
  } catch (e) { /* offline server: try again next time */ }
}

// A friendly break suggestion, never a scolding.
function showBreak() {
  breakShown = true;
  const panel = el("div", { class: "panel" },
    mascotSVG(), el("h2", {}, t("breakTime")),
    el("div", { class: "choices" },
      el("button", { class: "choice", "aria-label": "break", onclick: takeBreak }, "⏰"),
      el("button", { class: "choice", "aria-label": "keep playing", onclick: keepPlaying }, "▶")));
  openModal(panel);
  sfx("sparkle");
  speak(t("breakTime"));
}

function takeBreak() {
  closeModal();
  // The break is the "screen breaks" lesson from Computer Cove: look far, stretch, drink.
  lessonBreak(() => { sessionSeconds = 0; breakShown = false; welcomeScreen(); });
}

function keepPlaying() {
  closeModal();
  sessionSeconds = Math.max(0, settings.session_minutes * 60 - SNOOZE_SECONDS);
  breakShown = false;
}

// The daily limit: a calm goodnight screen. The parent's gear stays reachable.
function showLimit() {
  const first = !limitShown; // only announce it once, not on every re-check
  limitShown = true;
  keyHandler = null;
  const panel = el("div", { class: "panel" }, mascotSVG(), el("h2", {}, "😴 " + t("limitDone")));
  openModal(panel);
  if (first) speak(t("limitDone"));
}
