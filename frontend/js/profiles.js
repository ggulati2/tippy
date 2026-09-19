// Children: the "who is playing?" screen, switching between children, and the parent's Children tab.
//
// Each child has their own progress, stickers, settings and play limits (the server keeps one
// database per child). The child taps their own picture; no PIN is needed for that, because it only
// decides whose progress is shown. Adding, renaming and removing children needs the parent PIN.

let profileList = { profiles: [], active: 0, avatars: [] };

async function loadProfiles() {
  const { body } = await api("/api/profiles");
  profileList = body;
  return body;
}

const avatarOf = (id) => (profileList.profiles.find((p) => p.id === id) || {}).avatar || "🙂";

// Re-read the current child's settings (after the parent changed something about children).
async function reloadSettings() {
  const { body } = await api("/api/settings");
  settings = { ...settings, ...body };
  applyLook();
}

// Switch to another child. Play time so far is counted for the child who was playing, then the
// new child's settings and limits are loaded. `checkLimits: false` is used inside the parent area,
// where a "goodnight" pop-up must not cover the parent's screen (it is checked when the parent leaves).
async function switchChild(id, { checkLimits = true } = {}) {
  if (pendingSeconds > 0) {
    const seconds = pendingSeconds;
    pendingSeconds = 0;
    try { await api("/api/session/heartbeat", { method: "POST", body: JSON.stringify({ seconds }) }); } catch (e) { /* not important */ }
  }
  const { status, body } = await api("/api/profiles/select", { method: "POST", body: JSON.stringify({ id }) });
  if (status !== 200) return false;
  settings = { ...settings, ...body };
  applyLook();
  profileList.active = id;
  sessionSeconds = 0; breakShown = false; limitReached = false; limitShown = false;
  if (checkLimits) await refreshLimits();
  return true;
}

// The big "who is playing?" screen. It is shown at start-up when there is more than one child.
async function whoIsPlaying() {
  await loadProfiles();
  const cards = profileList.profiles.map((p) =>
    el("button", { class: "world child-card", onclick: async () => {
      sfx("play");
      if (await switchChild(p.id)) welcomeScreen();
    } }, el("span", { class: "icon" }, p.avatar), p.name || t("child.unnamed")));
  setScreen("who", el("h1", { class: "title" }, t("who.title")), el("div", { class: "worlds" }, ...cards));
  speak(t("who.title"));
}

// The small switch button (top left, only on the welcome and map screens when there are several children).
function updateWhoButton(screenName) {
  const button = $("#who-btn");
  const visible = settings.profile_count > 1 && ["welcome", "map"].includes(screenName);
  button.hidden = !visible;
  if (visible) button.textContent = avatarOf(settings.profile_id);
}

// ---------- Parent area: Children tab ----------

async function childrenTab(body) {
  await loadProfiles();
  const note = el("p", { class: "muted" }, t("children.note"));
  const message = el("p", { class: "llm-result" }, "");

  // Ask the server; show its message if it refuses (for example too many children).
  async function send(path, payload) {
    const { status, body: reply } = await api(path, { method: "POST", body: JSON.stringify(payload) });
    if (status === 200) { message.textContent = ""; await reloadSettings(); return true; }
    message.textContent = "⚠️ " + (typeof reply.detail === "string" ? reply.detail : t("children.error"));
    return false;
  }
  const refresh = () => parentPanel();

  const avatarSelect = (current, onPick) => {
    const select = el("select", { class: "avatar-select", "aria-label": "picture" },
      ...profileList.avatars.map((a) => el("option", a === current ? { value: a, selected: "selected" } : { value: a }, a)));
    select.addEventListener("change", () => onPick(select.value));
    return select;
  };

  const rows = profileList.profiles.map((p) => {
    const isActive = p.id === profileList.active;
    const name = el("input", { class: "text-input", type: "text", maxlength: "20", value: p.name, "aria-label": t("children.name") });
    name.addEventListener("change", async () => { await send(`/api/parent/profiles/${p.id}`, { name: name.value.trim() }); refresh(); });
    const actions = el("div", { class: "seg" },
      el("button", { class: isActive ? "on" : "", onclick: async () => {
        if (!isActive) { await switchChild(p.id, { checkLimits: false }); refresh(); }
      } }, isActive ? "✓ " + t("children.showing") : t("children.show")),
      el("button", { "aria-label": t("children.remove"), onclick: () => askRemove(p, row) }, "🗑️"));
    const row = el("div", { class: "row child-row" }, avatarSelect(p.avatar, async (a) => { await send(`/api/parent/profiles/${p.id}`, { avatar: a }); refresh(); }), name, actions);
    return row;
  });

  function askRemove(p, row) {
    if (profileList.profiles.length < 2) { message.textContent = "⚠️ " + t("children.last"); return; }
    const box = el("div", { class: "reset-box" }, el("p", {}, "⚠️ " + t("children.removeAsk").replace("{name}", p.name || t("child.unnamed"))),
      el("div", { class: "panel-actions inline" },
        el("button", { class: "big-btn exit-btn small-btn", onclick: async () => {
          if (await send(`/api/parent/profiles/${p.id}/delete`, { confirm: "DELETE" })) { await loadProfiles(); refresh(); }
        } }, t("children.removeYes")),
        el("button", { class: "big-btn blue small-btn", onclick: () => box.remove() }, t("dataCancel"))));
    row.after(box);
  }

  // Add a child.
  const newName = el("input", { class: "text-input", type: "text", maxlength: "20", placeholder: t("children.name"), "aria-label": t("children.name") });
  let newAvatar = profileList.avatars[profileList.profiles.length % profileList.avatars.length];
  let newLanguage = settings.language;
  const languagePick = toggleRow(t("language"), [["en", "English"], ["de", "Deutsch"]], newLanguage, (v) => { newLanguage = v; });
  languagePick.querySelector(".seg").addEventListener("click", (e) => {
    if (e.target.tagName !== "BUTTON") return;
    [...e.currentTarget.children].forEach((b) => b.classList.toggle("on", b === e.target));   // this form does not re-draw the page
  });
  const full = profileList.profiles.length >= 6;
  const addForm = full ? el("p", { class: "muted" }, t("children.max")) : el("div", { class: "add-child" },
    el("h3", {}, t("children.add")),
    el("div", { class: "row child-row" }, avatarSelect(newAvatar, (a) => { newAvatar = a; }), newName),
    languagePick,
    el("button", { class: "big-btn blue small-btn", onclick: async () => {
      if (!newName.value.trim()) { message.textContent = "⚠️ " + t("children.error"); return; }
      if (await send("/api/parent/profiles", { name: newName.value.trim(), avatar: newAvatar, language: newLanguage })) refresh();
    } }, "➕ " + t("children.addBtn")));

  body.replaceChildren(note, ...rows, message, addForm);
}
