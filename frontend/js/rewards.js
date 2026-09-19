// Progress, stars, stickers, the celebration screen and the sticker album.
// The rules (what earns a sticker, what unlocks) live on the server; this file
// only asks for the state and draws it.

let progress = null;       // latest state from /api/progress
let stickerCatalog = [];   // all stickers, from /api/stickers

async function loadProgress() {
  const [p, c] = await Promise.all([api("/api/progress"), api("/api/stickers")]);
  progress = p.body;
  stickerCatalog = c.body;
}

const stickerById = (id) => stickerCatalog.find((s) => s.id === id);
const stickerName = (s) => s.name[settings.language] || s.name.en;

// Save a finished level, then show the celebration. `next` runs when the child taps ▶.
async function completeLevel(world, level, next) {
  const { status, body } = await api("/api/progress/complete", {
    method: "POST", body: JSON.stringify({ world, level, stars: 3 }),
  });
  if (status !== 200) throw new Error("could not save progress");
  await loadProgress();
  celebrate(body.new_stickers, next);
}

// Falling emoji confetti. Purely decoration, so it is removed after a few seconds.
function confetti() {
  const layer = el("div", { class: "confetti" });
  const bits = ["⭐", "🎉", "✨", "🎈", "💛"];
  for (let i = 0; i < 28; i++) {
    const bit = el("span", {}, bits[i % bits.length]);
    bit.style.left = Math.random() * 100 + "%";
    bit.style.animationDelay = Math.random() * 1.2 + "s";
    bit.style.fontSize = 24 + Math.random() * 28 + "px";
    layer.append(bit);
  }
  setTimeout(() => layer.remove(), 5000);
  return layer;
}

function celebrate(newStickerIds, next) {
  const stars = el("div", { class: "stars" }, "⭐⭐⭐");
  const nodes = [el("h1", { class: "title" }, t("levelDone")), stars];
  const stickers = newStickerIds.map(stickerById).filter(Boolean);
  for (const s of stickers) {
    nodes.push(el("div", { class: "sticker-pop" }, el("span", { class: "sticker-emoji" }, s.emoji),
      el("span", {}, stickerName(s))));
  }
  const cheer = el("div", { class: "bubble" }, "\u00a0"); // Tippy's own line, filled in below
  nodes.push(cheer, el("button", { class: "big-btn play-btn", onclick: () => { sfx("play"); next(); } }, "▶"));
  setScreen("celebrate", ...nodes);
  $("#screen").append(confetti());
  sfx(stickers.length ? "sparkle" : "success");
  setTimeout(() => sfx("success"), 350);
  // The line comes from the cache (or the built-in bank), so it arrives instantly.
  mascotLine("success").then((line) => {
    cheer.textContent = line || t("levelDone");
    speak(stickers.length ? t("newSticker") : cheer.textContent);
  });
}

function albumScreen() {
  const earned = new Set(progress.stickers);
  const grid = el("div", { class: "album" });
  for (const s of stickerCatalog) {
    const got = earned.has(s.id);
    grid.append(el("div", { class: "album-slot" + (got ? " got" : "") },
      el("span", { class: "sticker-emoji" }, got ? s.emoji : "❔"),
      el("span", {}, got ? stickerName(s) : t("stickerLocked"))));
  }
  setScreen("album", el("h1", { class: "title" }, "📖 " + t("album")), grid);
  speak(t("album"));
}

// The row of level cards for a world (used by Keyboard Kingdom and Letter Land).
// `extra` is an optional element shown under the title.
async function levelPicker(worldId, icon, levelIcons, run, extra = null) {
  await loadProgress();
  const stars = progress.worlds[worldId].levels;
  const cards = levelIcons.map((levelIcon, i) => {
    const earned = stars[i + 1] || 0;
    return el("button", { class: "world level", onclick: () => { sfx("tap"); run(i + 1); } },
      el("span", { class: "icon" }, levelIcon),
      el("span", { class: "stars" }, earned ? "⭐".repeat(earned) : "☆☆☆"));
  });
  const nodes = [el("h1", { class: "title" }, `${icon} ${t("world." + worldId)}`)];
  if (extra) nodes.push(extra);
  nodes.push(el("div", { class: "worlds" }, ...cards));
  setScreen(worldId, ...nodes);
  speak(t("world." + worldId));
}
