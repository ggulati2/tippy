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
  // In a class the picture is what a child recognises; a missing name is not replaced by "Player".
  const cards = profileList.profiles.map((p) =>
    el("button", { class: "world child-card", onclick: async () => {
      sfx("play");
      if (await switchChild(p.id)) welcomeScreen();
    } }, el("span", { class: "icon" }, p.avatar), p.name || (profileList.classroom ? "" : t("child.unnamed"))));
  const grid = el("div", { class: "worlds" + (cards.length > 8 ? " class-grid" : "") }, ...cards);
  setScreen("who", el("h1", { class: "title" }, t("who.title")), grid);
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
    const pin = pinConfirmField();   // removing a child asks for the PIN again (brief section 6.4)
    const box = el("div", { class: "reset-box" }, el("p", {}, "⚠️ " + t("children.removeAsk").replace("{name}", p.name || t("child.unnamed"))),
      pin,
      el("div", { class: "panel-actions inline" },
        el("button", { class: "big-btn exit-btn small-btn", onclick: async () => {
          if (await send(`/api/parent/profiles/${p.id}/delete`, { confirm: "DELETE", pin: pin.value })) { await loadProfiles(); refresh(); }
          else { message.textContent = "⚠️ " + t("wrongPin"); pin.value = ""; }
        } }, t("children.removeYes")),
        el("button", { class: "big-btn blue small-btn", onclick: () => box.remove() }, t("dataCancel"))));
    row.after(box);
  }

  // Add a child.
  const newName = el("input", { class: "text-input", type: "text", maxlength: "20", placeholder: t("children.name"), "aria-label": t("children.name") });
  let newAvatar = profileList.avatars[profileList.profiles.length % profileList.avatars.length];
  let newLanguage = settings.language;
  const languagePick = toggleRow(t("language"), languageOptions(), newLanguage, (v) => { newLanguage = v; });
  languagePick.querySelector(".seg").addEventListener("click", (e) => {
    if (e.target.tagName !== "BUTTON") return;
    [...e.currentTarget.children].forEach((b) => b.classList.toggle("on", b === e.target));   // this form does not re-draw the page
  });
  const full = profileList.profiles.length >= profileList.max;
  const classroom = profileList.classroom;
  const addForm = full ? el("p", { class: "muted" }, t("children.max").replace("{max}", profileList.max)) : el("div", { class: "add-child" },
    el("h3", {}, t("children.add")),
    el("div", { class: "row child-row" }, avatarSelect(newAvatar, (a) => { newAvatar = a; }), newName),
    languagePick,
    el("button", { class: "big-btn blue small-btn", onclick: async () => {
      // A class is anonymous by default: there a nickname is optional, the picture is enough.
      if (!classroom && !newName.value.trim()) { message.textContent = "⚠️ " + t("children.error"); return; }
      if (await send("/api/parent/profiles", { name: newName.value.trim(), avatar: newAvatar, language: newLanguage })) refresh();
    } }, "➕ " + t("children.addBtn")));

  const classBox = el("div", { class: "class-box" },
    toggleRow(t("classMode"), [[false, t("setup.home")], [true, t("setup.classroom")]], classroom,
      async (v) => { await send("/api/parent/class", { classroom: v }); refresh(); }),
    ...(classroom ? [
      toggleRow(t("setDailyReset"), [[false, t("setOff")], [true, t("on")]], profileList.daily_reset,
        async (v) => { await send("/api/parent/class", { daily_reset: v }); refresh(); }),
      full ? "" : el("button", { class: "big-btn blue small-btn add-five", onclick: async () => {
        if (await send("/api/parent/class", { add: 5 })) refresh();
      } }, "➕ " + t("classAddFive")),
      await classOverview()] : []));

  body.replaceChildren(note, classBox, ...rows, message, addForm);
}

// The teacher's class overview (brief section 6.5): which stages each child has finished, and a CSV file of it.
async function classOverview() {
  const { body } = await api("/api/parent/class/overview");
  const done = (child, stage) => stage.worlds.every((w) => child.worlds[w] && child.worlds[w].done >= child.worlds[w].total);
  const label = (child) => child.name || child.avatar;
  const header = [t("classChild"), ...STAGES.map((s) => t(s.key)), t("statStars")];
  const rows = body.children.map((c) => [label(c), ...STAGES.map((s) => (done(c, s) ? "✓" : "")), c.stars]);
  const table = el("table", { class: "data-table class-table" },
    el("thead", {}, el("tr", {}, ...header.map((h) => el("th", {}, h)))),
    el("tbody", {}, ...body.children.map((c, i) => el("tr", {}, el("td", {}, `${c.avatar} ${c.name}`), ...rows[i].slice(1).map((v) => el("td", {}, String(v)))))));
  // A spreadsheet-safe CSV: every cell quoted, and a leading = + - @ neutralised so no cell runs as a formula.
  const cell = (v) => `"${String(v).replace(/"/g, '""').replace(/^([=+\-@])/, "'$1")}"`;
  const csv = [header, ...body.children.map((c, i) => [c.avatar + (c.name ? " " + c.name : ""), ...rows[i].slice(1)])]
    .map((r) => r.map(cell).join(",")).join("\r\n");
  const download = el("button", { class: "big-btn blue small-btn class-csv", onclick: () => {
    const link = el("a", { href: URL.createObjectURL(new Blob(["\ufeff" + csv], { type: "text/csv" })),
      download: `tippy-class-${new Date().toISOString().slice(0, 10)}.csv` });
    document.body.append(link); link.click(); link.remove();
  } }, "📄 " + t("classCsv"));
  return el("div", { class: "card class-overview" }, el("h3", {}, "🏫 " + t("classOverview")), table, download);
}
