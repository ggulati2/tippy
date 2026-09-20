// The four "everyday computer" worlds (Paint Place, Desktop Dock, Internet Island, Robot Helper): every level can be
// finished by a child who makes a few mistakes on the way, and every screen fits. (playthrough.js plays all worlds; this
// one is quicker and reports where a level got stuck.)
T.run(async () => {
  await T.wait(1200);
  const H = await T.parentLogin();
  await T.post("/api/parent/settings", { daily_limit_minutes: 0, session_minutes: 0 }, H);
  await T.post("/api/parent/unlock", { world: "all" }, H);
  await loadProgress();
  const only = (location.hash.slice(1) || "paint,desktop,internet,robot").split(",");
  for (const world of only) {
    openWorld(world); await T.wait(600);
    T.check(`${world}: the picker shows 5 levels`, document.querySelectorAll(".world.level").length === 5, document.querySelectorAll(".world.level").length);
    for (let i = 0; i < 5; i++) {
      const card = [...document.querySelectorAll(".world.level")][i];
      if (!card) { T.check(`${world} level ${i + 1} exists`, false); break; }
      T.act.droppedWrong = false; T.act.resetEveryday();
      card.click();
      let last = "";
      for (let tick = 0; tick < 300 && T.name() !== "celebrate"; tick++) {
        await T.wait(60);
        if (T.name() === "celebrate") break;
        T.checkFit(T.name());
        last = T.name() + " need=" + (document.querySelector("#screen").dataset.need || "");
        await T.act({ mistakes: true, doubleClickClose: true });
      }
      const ok = T.name() === "celebrate";
      T.check(`${world} level ${i + 1} can be finished`, ok, ok ? "" : "stuck on " + last);
      if (!ok) { openWorld(world); await T.wait(600); continue; }
      document.querySelector("#screen .play-btn").click();
      await T.wait(700);
    }
  }
  const p = await fetch("/api/progress").then((r) => r.json());
  T.check("all four worlds are complete", only.every((w) => p.worlds[w].complete), JSON.stringify(only.map((w) => Object.keys(p.worlds[w].levels).length)));
  T.check("the world stickers were earned", ["artist", "computer", "shield", "gear"].filter((s) => p.stickers.includes(s)).length === only.length * 1 || only.length < 4);
});
