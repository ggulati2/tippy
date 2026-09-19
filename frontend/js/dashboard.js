// The parent area: four tabs (Progress, Settings, Online helper, Data).
// Everything here is for the parent only. The child never sees these numbers.

let parentTab = "progress";
const TABS = [["progress", "📊", "tabProgress"], ["settings", "⚙️", "tabSettings"], ["children", "👧", "tabChildren"], ["helper", "🤖", "tabHelper"], ["data", "🗄️", "tabData"]];

async function parentPanel() {
  const body = el("div", { class: "tab-body" });
  // The online helper tab only exists when the online helper is switched on in .env (LLM_MODE=live).
  const visibleTabs = TABS.filter(([id]) => id !== "helper" || settings.online_helper);
  if (!visibleTabs.some(([id]) => id === parentTab)) parentTab = "progress";
  const tabs = el("div", { class: "tabs" }, ...visibleTabs.map(([id, icon, key]) =>
    el("button", { class: "tab" + (id === parentTab ? " on" : ""), onclick: () => { parentTab = id; parentPanel(); } }, `${icon} ${t(key)}`)));
  const panel = el("div", { class: "panel wide" },
    el("h2", {}, "🔓 " + t("parentArea") + (settings.profile_count > 1 ? ` · ${avatarOf(settings.profile_id)} ${settings.child_name || t("child.unnamed")}` : "")), tabs, body,
    // Exit and Back stay visible at the bottom even when the tab scrolls.
    el("div", { class: "panel-actions" },
      el("button", { class: "big-btn exit-btn small-btn", onclick: exitApp }, t("exitApp")),
      el("button", { class: "big-btn blue small-btn", onclick: leaveParentArea }, t("back"))));
  openModal(panel);
  const render = { progress: progressTab, settings: settingsTab, children: childrenTab, helper: helperTab, data: dataTab }[parentTab];
  await render(body);
}

async function leaveParentArea() {
  await refreshLimits();  // the parent may have changed the limits; if the limit still applies this shows the goodnight screen
  parentToken = null;
  if (!limitReached) closeModal();
  welcomeScreen();
}

// ---------- Small helpers ----------

const SVG = "http://www.w3.org/2000/svg";
function svgEl(tag, attrs = {}, ...children) {
  const node = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  for (const c of children) node.append(c);
  return node;
}

const shortDate = (iso, options = { month: "short", day: "numeric" }) =>
  new Date(iso + "T00:00:00").toLocaleDateString(settings.language, options);

// A collapsible table with the same numbers as a chart, for screen readers and exact values.
function tableView(headings, rows) {
  const table = el("table", { class: "data-table" },
    el("thead", {}, el("tr", {}, ...headings.map((h) => el("th", {}, h)))),
    el("tbody", {}, ...rows.map((row) => el("tr", {}, ...row.map((cell) => el("td", {}, String(cell)))))));
  return el("details", { class: "table-view" }, el("summary", {}, t("tableView")), table);
}

function tile(icon, label, value) {
  return el("div", { class: "tile" }, el("div", { class: "tile-value" }, `${icon} ${value}`), el("div", { class: "tile-label" }, label));
}

// ---------- Charts (single series, one blue, thin marks, quiet grid) ----------

const CHART = { W: 560, H: 170, L: 40, R: 24, T: 20, B: 30 };
const INK = "#23395b", MUTED = "#6b7c93", GRID = "#e6e4dd", BLUE = "#2a78d6", SURFACE = "#ffffff";

function chartFrame(label) {
  return svgEl("svg", { viewBox: `0 0 ${CHART.W} ${CHART.H}`, class: "chart", role: "img", "aria-label": label });
}

function chartText(x, y, text, anchor = "middle", weight = 600, fill = MUTED) {
  const node = svgEl("text", { x, y, "text-anchor": anchor, "font-size": 12, "font-weight": weight, fill });
  node.textContent = text;
  return node;
}

function yGrid(svg, max, unit) {
  const { W, H, L, R, T, B } = CHART;
  for (const v of [0, max / 2, max]) {
    const y = T + (H - T - B) * (1 - v / max);
    svg.append(svgEl("line", { x1: L, x2: W - R, y1: y, y2: y, stroke: GRID, "stroke-width": 1 }));
    svg.append(chartText(L - 6, y + 4, `${Math.round(v)}${unit}`, "end"));
  }
}

// Accuracy by day: a line with a dot per day. Only the last value gets a label; hover shows any day.
function accuracyChart(trend) {
  const { W, H, L, R, T, B } = CHART;
  const svg = chartFrame(t("chartAccuracy"));
  yGrid(svg, 100, "%");
  if (!trend.length) { svg.append(chartText(W / 2, H / 2, t("chartEmpty"), "middle", 700)); return svg; }
  const x = (i) => (trend.length === 1 ? (L + W - R) / 2 : L + ((W - L - R) * i) / (trend.length - 1));
  const y = (v) => T + (H - T - B) * (1 - v / 100);
  svg.append(svgEl("polyline", { points: trend.map((p, i) => `${x(i)},${y(p.accuracy)}`).join(" "), fill: "none",
    stroke: BLUE, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));
  trend.forEach((p, i) => {
    const tip = svgEl("title", {}); tip.textContent = `${shortDate(p.day)}: ${p.accuracy}% (${p.attempts})`;
    svg.append(svgEl("circle", { cx: x(i), cy: y(p.accuracy), r: 5, fill: BLUE, stroke: SURFACE, "stroke-width": 2 }));
    svg.append(svgEl("circle", { cx: x(i), cy: y(p.accuracy), r: 14, fill: "transparent" }, tip)); // bigger hover target
  });
  const last = trend[trend.length - 1];
  svg.append(chartText(x(trend.length - 1), y(last.accuracy) - 12, `${last.accuracy}%`, "end", 800, INK));
  svg.append(chartText(x(0), H - 8, shortDate(trend[0].day), trend.length === 1 ? "middle" : "start"));
  if (trend.length > 1) svg.append(chartText(x(trend.length - 1), H - 8, shortDate(last.day), "end"));
  return svg;
}

// Minutes played per day for the last week: thin bars with a rounded top, sitting on the baseline.
function playChart(days) {
  const { W, H, L, R, T, B } = CHART;
  const svg = chartFrame(t("chartPlay"));
  const max = Math.max(10, Math.ceil(Math.max(...days.map((d) => d.minutes)) / 5) * 5);
  yGrid(svg, max, "");
  const band = (W - L - R) / days.length, barW = 26, base = H - B, top = Math.max(...days.map((d) => d.minutes));
  days.forEach((d, i) => {
    const cx = L + band * i + band / 2, h = (d.minutes / max) * (H - T - B), x0 = cx - barW / 2, r = 4;
    if (h > 0) {
      const tip = svgEl("title", {}); tip.textContent = `${shortDate(d.day)}: ${d.minutes} min`;
      const rr = Math.min(r, h);
      svg.append(svgEl("path", { fill: BLUE, d: `M${x0},${base} V${base - h + rr} Q${x0},${base - h} ${x0 + rr},${base - h} H${x0 + barW - rr} Q${x0 + barW},${base - h} ${x0 + barW},${base - h + rr} V${base} Z` }, tip));
      if (d.minutes === top || i === days.length - 1) svg.append(chartText(cx, base - h - 6, String(d.minutes), "middle", 800, INK));
    }
    svg.append(chartText(cx, H - 8, shortDate(d.day, { weekday: "short" })));
  });
  return svg;
}

function chartCard(title, chart, table) {
  return el("div", { class: "card" }, el("h3", {}, title), chart, table);
}

// ---------- Heat map on the keyboard ----------
// Colour = share of mistakes, one blue from light (few) to dark (many). Grey = no data yet.

const HEAT_RAMP = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"];
const HEAT_FULL_AT = 0.4; // 40% mistakes or more gets the darkest colour

function heatStep(mistakes) {
  const position = Math.min(1, mistakes / HEAT_FULL_AT) * (HEAT_RAMP.length - 1);
  const low = Math.floor(position), high = Math.min(HEAT_RAMP.length - 1, low + 1), mix = position - low;
  const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const [a, b] = [rgb(HEAT_RAMP[low]), rgb(HEAT_RAMP[high])];
  const color = "#" + a.map((v, i) => Math.round(v + (b[i] - v) * mix).toString(16).padStart(2, "0")).join("");
  return { color, dark: position > 1.6 };
}

// Colour the keys of a board by how often they went wrong (darker = more mistakes, grey = no data).
function paintHeat(board, stats, names) {
  for (const name of names) {
    const node = board.element(name);
    if (!node) continue;
    const stat = stats[name];
    node.style.setProperty("--c", "#eeeeea");
    if (!stat) { node.style.background = "#eeeeea"; node.style.opacity = ".7"; node.title = `${name}: ${t("heatNone")}`; continue; }
    const { color, dark } = heatStep(1 - stat.accuracy);
    node.style.background = color;
    node.style.color = dark ? "#ffffff" : INK;
    node.title = `${name}: ${Math.round(stat.accuracy * 100)}% (${stat.attempts})`;
  }
}

function heatMap(keys) {
  const board = renderKeyboard();
  const stats = Object.fromEntries(keys.map((k) => [k.key, k]));
  paintHeat(board, stats, Object.keys(KEY_LABELS).concat("QWERTYUIOPASDFGHJKLZXCVBNMÖÄÜ".split("")));
  // Number Land keys get their own small pad once the child has practised digits.
  const pad = keys.some((k) => /^[0-9]$/.test(k.key)) ? renderNumpad() : null;
  if (pad) { paintHeat(pad, stats, "0123456789".split("")); pad.node.classList.add("heat", "heat-pad"); }
  const legend = el("div", { class: "heat-legend" }, el("span", {}, t("heatLess")),
    el("span", { class: "heat-bar" }), el("span", {}, t("heatMore")), el("span", { class: "heat-none" }), el("span", {}, t("heatNone")));
  const rows = [...keys].sort((a, b) => a.accuracy - b.accuracy)
    .map((k) => [k.key, `${Math.round(k.accuracy * 100)}%`, k.attempts, `${(k.avg_ms / 1000).toFixed(1)} s`]);
  board.node.classList.add("heat");
  return el("div", { class: "card" }, el("h3", {}, t("heatTitle")), board.node, ...(pad ? [el("h4", {}, "🔢 " + t("world.numbers")), pad.node] : []), legend,
    tableView([t("colKey"), t("colAccuracy"), t("colTries"), t("colSpeed")], rows));
}

// ---------- Weekly summary ----------

function summaryCard() {
  const content = el("div", { class: "summary-body" }, t("summaryLoading"));
  const badge = el("span", { class: "badge" }, "");
  const refresh = el("button", { class: "chip", onclick: () => load(true) }, "↻ " + t("summaryRefresh"));

  async function load(force) {
    content.textContent = t("summaryLoading");
    const { status, body } = await api("/api/parent/summary" + (force ? "?refresh=true" : ""));
    if (status !== 200) { content.textContent = t("chartEmpty"); return; }
    badge.textContent = body.source === "llm" ? "🤖 " + t("summaryLlm") : "📝 " + t("summaryBuiltin");
    content.replaceChildren(...[["strengths", "summaryStrengths"], ["practice", "summaryPractice"], ["tips", "summaryTips"]].map(([field, label]) =>
      el("p", {}, el("strong", {}, t(label) + ": "), body[field]))); // textContent: escaped
  }
  load(false);
  return el("div", { class: "card wide-card" }, el("div", { class: "row" }, el("h3", {}, "📝 " + t("summaryTitle")), refresh), badge, content);
}

// ---------- Tab: Progress ----------

async function progressTab(body) {
  const { body: d } = await api("/api/parent/dashboard");
  const accuracy = d.overall_accuracy === null ? "–" : `${d.overall_accuracy}%`;
  body.replaceChildren(
    el("div", { class: "tiles" },
      tile("🔥", t("statStreak"), d.streak), tile("⭐", t("statStars"), d.total_stars), tile("📖", t("statStickers"), d.sticker_count),
      tile("⏱️", t("statToday"), d.today_minutes), tile("🔤", `${t("statLetters")} (✔ ${d.letters.mastered.length})`, d.letters.unlocked.length),
      tile("🎯", t("statAccuracy"), accuracy)),
    el("div", { class: "cards" },
      chartCard(t("chartAccuracy"), accuracyChart(d.trend),
        tableView([t("colDay"), t("colAccuracy"), t("colTries")], d.trend.map((p) => [shortDate(p.day), p.accuracy + "%", p.attempts]))),
      chartCard(t("chartPlay"), playChart(d.play_minutes),
        tableView([t("colDay"), t("colMinutes")], d.play_minutes.map((p) => [shortDate(p.day), p.minutes])))),
    heatMap(d.keys),
    summaryCard());
}

// ---------- Tab: Settings ----------

const INTERESTS = [["animals", "🐾"], ["space", "🚀"], ["dinosaurs", "🦖"], ["vehicles", "🚗"]];

async function settingsTab(body) {
  const { body: d } = await api("/api/parent/dashboard");
  await loadProgress();
  const chosen = new Set(d.interests);
  const interestButtons = INTERESTS.map(([id, icon]) => el("button", {
    class: chosen.has(id) ? "on" : "",
    onclick: () => {
      if (chosen.has(id) && chosen.size === 1) return; // at least one interest stays selected
      chosen.has(id) ? chosen.delete(id) : chosen.add(id);
      saveSetting({ interests: [...chosen] });
    } }, `${icon} ${t("interest." + id)}`));

  const worldButtons = WORLDS.map(([id, icon]) => {
    const open = progress.worlds[id].unlocked;
    return el("button", { class: open ? "on" : "", onclick: async () => {
      await api("/api/parent/unlock", { method: "POST", body: JSON.stringify({ world: id }) });
      sfx("tap"); parentPanel();
    } }, `${open ? "🔓" : "🔒"} ${icon}`);
  });

  const minutes = (label, key, values, current) => toggleRow(label, values.map((v) => [v, v === 0 ? t("setOff") : `${v} ${t("setMinutes")}`]), current, (v) => saveSetting({ [key]: v }));

  body.replaceChildren(el("div", { class: "settings-grid" },
    toggleRow(t("language"), languageOptions(), settings.language, (v) => saveSetting({ language: v })),
    toggleRow(t("keyboardLayout"), Object.entries(KEYBOARD_NAMES), settings.keyboard_layout, (v) => saveSetting({ keyboard_layout: v })),
    toggleRow(t("letterCase"), [["upper", "ABC"], ["lower", "abc"]], settings.letter_case, (v) => saveSetting({ letter_case: v })),
    toggleRow(t("voice"), [[true, t("on")], [false, t("off")]], settings.voice_on, (v) => saveSetting({ voice_on: v })),
    toggleRow(t("sound"), [[true, t("on")], [false, t("off")]], settings.sound_on, (v) => saveSetting({ sound_on: v })),
    toggleRow(t("setFont"), [[1, "A"], [1.125, "A+"], [1.25, "A++"]], settings.font_scale || 1, (v) => saveSetting({ font_scale: v })),
    toggleRow(t("setNumpad"), [[true, t("on")], [false, t("off")]], !!settings.has_numpad, (v) => saveSetting({ has_numpad: v })),
    toggleRow(t("setMotion"), [[false, t("on")], [true, t("off")]], !!settings.reduce_motion, (v) => saveSetting({ reduce_motion: v })),
    el("div", { class: "row" }, el("span", {}, t("setPin")), el("button", { class: "big-btn blue small-btn", onclick: changePinFlow }, "🔑 " + t("setPinBtn"))),
    textRow(t("childName"), "child_name", settings.child_name, 20),
    textRow(t("favoriteWord"), "favorite_word", settings.favorite_word, 15),
    el("div", { class: "row" }, el("span", {}, t("setInterests")), el("div", { class: "seg wrap" }, ...interestButtons)),
    minutes(t("setSession"), "session_minutes", [5, 10, 15, 20, 0], settings.session_minutes),
    minutes(t("setDaily"), "daily_limit_minutes", [0, 30, 45, 60, 90], settings.daily_limit_minutes),
    toggleRow(t("setAsk"), [[true, t("on")], [false, t("off")]], settings.ask_tippy, (v) => saveSetting({ ask_tippy: v })),
    el("div", { class: "row" }, el("span", {}, t("setUnlock")), el("div", { class: "seg wrap" }, ...worldButtons)),
    el("button", { class: "big-btn blue small-btn", onclick: async () => {
      await api("/api/parent/unlock", { method: "POST", body: JSON.stringify({ world: "all" }) });
      sfx("success"); parentPanel();
    } }, "🔓 " + t("unlockAll"))));
}

// ---------- Tab: Online helper ----------

const MODEL_SUGGESTIONS = ["nvidia/nemotron-3-super-120b-a12b:free", "deepseek/deepseek-v4-flash-0731:free",
  "google/gemma-4-26b-a4b-it:free", "google/gemma-4-31b-it:free"];

async function helperTab(body) {
  const { body: status } = await api("/api/parent/status");
  const list = el("datalist", { id: "model-list" }, ...MODEL_SUGGESTIONS.map((m) => el("option", { value: m })));
  const modelInput = el("input", { class: "text-input wide-input", type: "text", list: "model-list", maxlength: "80", value: status.model,
    onchange: () => saveSetting({ openrouter_model: modelInput.value.trim() }) });
  body.replaceChildren(
    llmSection(status),
    el("div", { class: "row" }, el("span", {}, t("helperModel")), modelInput, list),
    el("div", { class: "row" }, el("span", {}, t("helperFallback")), el("span", { class: "muted" }, status.fallback_model)),
    el("p", { class: "muted" }, t("helperNote")));
}

// The online helper's status, cost and a "Test connection" button. Parent area only.
function llmSection(status) {
  let line;
  if (status.mode === "mock") line = "🧪 " + t("llmMock");
  else if (!status.key_set) line = "🔑 " + t("llmNoKey");
  else if (status.online === false) line = "🟡 " + t("llmOffline");
  else line = "🟢 " + t("llmLive");

  const result = el("span", { class: "llm-result" }, "");
  const testButton = el("button", { class: "chip", onclick: async () => {
    result.textContent = "…";
    const { body } = await api("/api/parent/llm/test", { method: "POST" });
    result.textContent = body.ok
      ? `✓ ${t("llmOk")} (${body.model}${body.latency_ms ? ", " + body.latency_ms + " ms" : ""})`
      : `✗ ${t("llmFail")}: ${body.error}`;
  } }, "🔌 " + t("llmTest"));

  const details = [`${t("llmModel")}: ${status.model}`, `${t("llmToday")}: ${status.requests}/${status.cap}`,
                   `${t("llmCost")}: $${Number(status.cost_usd).toFixed(4)}`].join("  ·  ");
  return el("div", { class: "llm-box" },
    el("div", { class: "row" }, el("span", {}, t("status")), el("span", {}, line)),
    status.mode === "live" ? el("div", { class: "llm-details" }, details) : "",
    el("div", { class: "row" }, testButton, result));
}

// ---------- Tab: Data ----------

let restoreNotice = "";   // shown once after a restore, because restoring redraws the parent area

async function dataTab(body) {
  const message = el("span", { class: "llm-result" }, restoreNotice);
  restoreNotice = "";
  const resetBox = el("div", { class: "reset-box" });

  async function exportBackup() {
    const { body: data } = await api("/api/parent/export");
    const link = el("a", { href: URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })),
      download: `tippy-backup-${new Date().toISOString().slice(0, 10)}.json` });
    document.body.append(link); link.click(); link.remove();
    message.textContent = "✓ " + t("dataExported");
  }

  function askReset() {
    resetBox.replaceChildren(el("p", {}, "⚠️ " + t("dataResetAsk")), el("div", { class: "panel-actions inline" },
      el("button", { class: "big-btn exit-btn small-btn", onclick: async () => {
        await api("/api/parent/reset", { method: "POST", body: JSON.stringify({ confirm: "RESET" }) });
        resetBox.replaceChildren(el("p", {}, "✓ " + t("dataDone")));
      } }, t("dataResetYes")),
      el("button", { class: "big-btn blue small-btn", onclick: () => resetBox.replaceChildren() }, t("dataCancel"))));
  }

  // Restore: pick a file, then choose between replacing the shown child and adding a new one.
  const restoreBox = el("div", { class: "reset-box restore-box" });
  const fileInput = el("input", { type: "file", accept: ".json,application/json", hidden: "hidden", "aria-label": t("dataRestore") });
  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    fileInput.value = "";
    if (!file) return;
    restoreBox.replaceChildren();
    if (file.size > 5 * 1024 * 1024) { message.textContent = "⚠️ " + t("dataRestoreBig"); return; }
    const text = await file.text();
    try { JSON.parse(text); } catch (e) { message.textContent = "⚠️ " + t("dataRestoreBad"); return; }
    const name = settings.child_name || t("child.unnamed");
    async function restoreInto(target) {
      const { status, body: reply } = await api("/api/parent/import?target=" + target, { method: "POST", body: text });
      if (status !== 200) {
        message.textContent = "⚠️ " + (status === 413 ? t("dataRestoreBig") : ["bad-file", "empty", "too-big"].includes(reply.detail) || typeof reply.detail !== "string" ? t("dataRestoreBad") : reply.detail);
        restoreBox.replaceChildren();
        return;
      }
      restoreNotice = "✓ " + t("dataRestored").replace("{levels}", reply.restored.progress).replace("{stickers}", reply.restored.stickers);
      await reloadSettings();
      parentPanel();
    }
    restoreBox.replaceChildren(el("p", {}, "⚠️ " + t("dataRestoreAsk").replace("{name}", name)), el("div", { class: "panel-actions inline" },
      el("button", { class: "big-btn exit-btn small-btn", onclick: () => restoreInto("current") }, t("dataRestoreReplace").replace("{name}", name)),
      el("button", { class: "big-btn blue small-btn", onclick: () => restoreInto("new") }, t("dataRestoreNew")),
      el("button", { class: "big-btn small-btn", onclick: () => restoreBox.replaceChildren() }, t("dataCancel"))));
  });

  body.replaceChildren(
    el("p", {}, "🔒 " + t("dataWhere")),
    el("div", { class: "row" }, el("button", { class: "big-btn blue small-btn", onclick: exportBackup }, "💾 " + t("dataExport")), message),
    el("div", { class: "row" }, el("button", { class: "big-btn blue small-btn", onclick: () => fileInput.click() }, "📂 " + t("dataRestore")), fileInput),
    restoreBox,
    el("div", { class: "row" }, el("button", { class: "big-btn small-btn danger", onclick: askReset }, "🗑️ " + t("dataReset"))),
    resetBox);
}
