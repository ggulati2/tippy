// Things a real child does that a polite script would not: leaving a game with Home at any moment,
// mashing keys, pressing shortcuts, clicking everything many times, opening the parent pop-up again and again.
T.run(async () => {
  await T.wait(1200);
  const H = await T.parentLogin();
  await T.post("/api/parent/settings", { daily_limit_minutes: 0, session_minutes: 0 }, H);
  await T.post("/api/parent/unlock", { world: "all" }, H);
  await loadProgress();

  // A) Leave every level with Home at three different moments. A game's pending step must never
  //    fire afterwards (it once popped a "level done" screen on top of the home screen).
  let leaks = [];
  for (const [world, levels] of [["mouse", 4], ["keyboard", 5], ["letters", 5], ["name", 3], ["words", 5], ["sentences", 3], ["basics", 6], ["safety", 6], ["quiz", 4], ["numbers", 6]]) {
    for (let i = 0; i < levels; i++) for (const delay of [200, 900, 2500]) {
      await loadProgress(); openWorld(world); await T.wait(400);
      [...document.querySelectorAll(".world.level")][i].click();
      const until = Date.now() + delay;
      while (Date.now() < until) { await T.act(); await T.wait(80); }
      document.querySelector("#home-btn").click();
      await T.wait(4000);                                   // long enough for any leftover timer
      if (T.name() !== "welcome") leaks.push(`${world} L${i + 1} after ${delay}ms -> "${T.name()}"`);
    }
  }
  T.check("leaving with Home never leaves a stale screen behind", leaks.length === 0, leaks.join("; "));

  // B) Key mashing: junk keys and many letters on every typing screen.
  const junk = ["!", "@", "#", "1", "0", "Tab", "Escape", "F5", "F12", "ArrowLeft", "Delete", "Home", "CapsLock", "Dead", "Unidentified", "Meta", "Control", "Alt", "ContextMenu", "PageDown", "Process"];
  for (const [world, i] of [["keyboard", 0], ["keyboard", 4], ["letters", 0], ["name", 0], ["words", 0], ["sentences", 0]]) {
    await loadProgress(); openWorld(world); await T.wait(400);
    [...document.querySelectorAll(".world.level")][i].click(); await T.wait(300);
    for (let t = 0; t < 400; t++) T.key(junk[t % junk.length]);
    for (let t = 0; t < 200; t++) T.key("abcdefghijklmnopqrstuvwxyz"[t % 26]);
    await T.wait(500);
    T.check(`mashing keys in ${world} ${i + 1} leaves a sane screen`, ["celebrate", "kb-1", "kb-5", "letters", "name", "words", "sentences"].includes(T.name()), T.name());
  }
  await loadProgress(); openWorld("free"); await T.wait(500);
  for (let t = 0; t < 300; t++) T.key(junk[t % junk.length]);
  for (let t = 0; t < 40; t++) T.key("a");
  await T.wait(300);
  const tiles = document.querySelectorAll(".free-text .slot").length;
  T.check("Free Play stops at 14 letters", tiles === 14, tiles + " letters");

  // C) Shortcuts must not reach the browser while a game runs.
  openWorld("letters"); await T.wait(300); [...document.querySelectorAll(".world.level")][0].click(); await T.wait(300);
  const shortcuts = [["w", { ctrlKey: true }], ["r", { metaKey: true }], ["F5", {}], ["F4", { altKey: true }], ["l", { ctrlKey: true }], ["Tab", {}], [" ", {}], ["Backspace", {}]];
  const unblocked = shortcuts.filter(([k, x]) => !T.key(k, x).defaultPrevented).map(([k]) => k);
  T.check("shortcuts and browser keys are blocked during play", unblocked.length === 0, "not blocked: " + unblocked.join(","));

  // D) Clicking everything 30 times.
  for (const [world, i] of [["mouse", 0], ["mouse", 2], ["basics", 0], ["basics", 4]]) {
    await loadProgress(); openWorld(world); await T.wait(300);
    [...document.querySelectorAll(".world.level")][i].click(); await T.wait(300);
    for (let t = 0; t < 30; t++) { document.querySelectorAll("#screen button").forEach((b) => b.click()); if (t % 3 === 0) await T.wait(30); }
    await T.wait(2500);
  }

  // E) The parent gear pressed five times opens one pop-up; Escape closes it.
  document.querySelector("#home-btn").click(); await T.wait(300);
  for (let t = 0; t < 5; t++) document.querySelector("#parent-btn").click();
  await T.wait(300);
  T.check("gear pressed five times opens one pop-up", T.modalCount() === 1, T.modalCount());
  T.key("Escape"); await T.wait(200);
  T.check("Escape closes it", T.modalCount() === 0, T.modalCount());
});
