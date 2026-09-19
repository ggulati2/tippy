// First-run setup and "change PIN".
//
// The very first time Tippy starts (no PIN saved yet) the parent is guided through three
// short steps: language, choose a PIN, and the child's first name plus a daily play limit.
// The PIN is stored on this computer only, as a salted hash (never as plain text).

let setupActive = false; // while true, Escape cannot close the setup pop-up

// A pop-up with a number pad. The global key handler in app.js sends real keyboard digits to
// panel.pinPress / pinBack / pinSubmit, so the parent can type the PIN or click it.
function keypadPanel(title, hint, onSubmit, onBack) {
  let entered = "";
  const dots = el("div", { class: "pin-dots" });
  const msg = el("div", { class: "pin-msg" }, hint);
  const refresh = () => { dots.textContent = "●".repeat(entered.length) || " "; };
  const press = (d) => { if (entered.length < 8) { entered += d; refresh(); sfx("key"); } };
  const back = () => { entered = entered.slice(0, -1); refresh(); };
  const submit = () => {
    const value = entered;
    entered = ""; refresh();
    if (value.length < 4) { msg.textContent = t("setup.pinShort"); return; }
    onSubmit(value, (text) => { msg.textContent = text; });
  };
  const keys = "123456789".split("").map((d) => el("button", { onclick: () => press(d) }, d));
  keys.push(el("button", { onclick: back }, "⌫"), el("button", { onclick: () => press("0") }, "0"), el("button", { onclick: submit }, "✔"));
  refresh();
  const panel = el("div", { class: "panel" }, el("h2", {}, "🔒 " + title), dots, msg, el("div", { class: "keypad" }, ...keys),
    onBack ? el("button", { class: "big-btn blue", onclick: onBack }, t("back")) : "");
  panel.pinPress = press; panel.pinBack = back; panel.pinSubmit = submit;
  return panel;
}

// Ask for a new PIN twice. Calls done(pin) when both entries match.
function chooseNewPin(done, onBack) {
  const first = (hint) => openModal(keypadPanel(t("setup.choosePin"), hint || t("setup.pinNote"), (pin) => confirm(pin), onBack));
  const confirm = (pin) => openModal(keypadPanel(t("setup.confirmPin"), "", (again, say) => {
    if (again === pin) done(pin); else first(t("setup.mismatch"));
  }, () => first()));
  first();
}

function setupWizard() {
  setupActive = true;
  const data = { pin: "", language: settings.language, child_name: "", daily_limit_minutes: 30 };
  $("#parent-btn").hidden = true;

  function stepLanguage() {
    // Shown in every language at once, because the parent has not chosen one yet.
    openModal(el("div", { class: "panel" }, mascotSVG(), el("h2", {}, "Welcome · Willkommen · Bienvenido"),
      el("div", { class: "choices" },
        ...languageOptions().map(([code, label]) =>
          el("button", { class: "big-btn blue", onclick: () => { data.language = settings.language = code; stepPin(); } }, label)))));
  }

  function stepPin() { chooseNewPin((pin) => { data.pin = pin; stepBasics(); }, stepLanguage); }

  function stepBasics() {
    const name = el("input", { class: "text-input", type: "text", maxlength: "20", value: data.child_name,
      onchange: () => { data.child_name = name.value.trim(); } });
    const limit = toggleRow(t("setDaily"), [0, 30, 45, 60].map((v) => [v, v === 0 ? t("setOff") : `${v} ${t("setMinutes")}`]),
      data.daily_limit_minutes, (v) => { data.daily_limit_minutes = v; data.child_name = name.value.trim(); stepBasics(); });
    openModal(el("div", { class: "panel wide" }, el("h2", {}, t("setup.basics")),
      el("div", { class: "row" }, el("span", {}, t("childName")), name), limit,
      el("p", { class: "muted" }, t("setup.later")),
      el("button", { class: "big-btn play-btn", onclick: finish }, "▶ " + t("setup.start"))));
  }

  async function finish() {
    const { body } = await api("/api/setup", { method: "POST", body: JSON.stringify({ ...data, child_name: data.child_name }) });
    settings = { ...settings, ...body };
    applyLook();
    setupActive = false;
    $("#parent-btn").hidden = false;
    closeModal();
    startLimits();
    welcomeScreen();
  }

  stepLanguage();
}

// Parent area, Settings: change the PIN. The parent signs in again with the new PIN afterwards.
function changePinFlow() {
  chooseNewPin(async (pin) => {
    await api("/api/parent/pin", { method: "POST", body: JSON.stringify({ pin }) });
    parentToken = null;
    openModal(pinPad());
  }, parentPanel);
}
