// Plays every level of every world like a child would, including mistakes, and checks that each
// one can be finished, that nothing throws, and (unless the text is enlarged) that every screen fits.
// Hash: "<lang>:<font scale>", for example "de:1".
T.run(async () => {
  await T.wait(1200);
  const [lang, scale] = (location.hash.slice(1) || "en:1").split(":");
  const H = await T.parentLogin();
  const saved = await fetch("/api/parent/settings", { method: "POST", headers: { "Content-Type": "application/json", ...H }, body: JSON.stringify({
    language: lang, keyboard_layout: lang === "de" ? "qwertz" : "qwerty", child_name: lang === "de" ? "Jürgen" : "Mia",
    favorite_word: "hund", font_scale: Number(scale || 1), daily_limit_minutes: 0, session_minutes: 0 }) }).then((r) => r.json());
  await T.post("/api/parent/unlock", { world: "all" }, H);
  settings = { ...settings, ...saved }; applyLook(); await loadProgress();

  async function playLevel(world, i) {
    const card = [...document.querySelectorAll(".world.level")][i];
    if (!card) { T.check(`${world} level ${i + 1} exists`, false); return false; }
    T.act.droppedWrong = false;
    card.click();
    for (let tick = 0; tick < 4000 && T.name() !== "celebrate"; tick++) {
      await T.wait(60);
      if (T.name() === "celebrate") break;
      T.checkFit(T.name());
      await T.act({ mistakes: true, doubleClickClose: true });
    }
    const ok = T.name() === "celebrate";
    T.check(`${world} level ${i + 1} can be finished`, ok, ok ? "" : "stuck on screen " + T.name());
    if (!ok) return false;
    document.querySelector("#screen .play-btn").click();   // "next" on the celebration screen
    await T.wait(700);
    return true;
  }

  for (const [world, levels] of [["mouse", 4], ["keyboard", 5], ["letters", 5], ["words", 5], ["sentences", 5], ["basics", 6], ["numbers", 6]]) {
    await loadProgress(); openWorld(world); await T.wait(600);
    for (let i = 0; i < levels; i++) if (!(await playLevel(world, i))) { openWorld(world); await T.wait(600); }
  }

  await loadProgress(); openWorld("free"); await T.wait(800);
  for (let tick = 0; tick < 300 && T.name() !== "celebrate"; tick++) { await T.act(); await T.wait(60); }
  T.check("Free Play: three scenes earn the sticker", T.name() === "celebrate", T.name());

  const p = await fetch("/api/progress").then((r) => r.json());
  T.check("stickers were earned", p.stickers.length >= 20, p.stickers.length + " stickers");
  const done = Object.fromEntries(Object.entries(p.worlds).map(([k, v]) => [k, Object.keys(v.levels).length]));
  T.check("every world is complete in the saved progress", JSON.stringify(done) === JSON.stringify({ mouse: 4, keyboard: 5, letters: 5, words: 5, sentences: 5, basics: 6, free: 1, numbers: 6 }), JSON.stringify(done));
});
