// Keyboard Kingdom bonus games: the arrow keys really move the bunny to the carrot, a wrong arrow does
// nothing, and Caps Lock toggles between big and small letters.
T.run(async () => {
  await T.wait(1500);
  const H = await T.parentLogin();
  await T.post("/api/parent/settings", { daily_limit_minutes: 0, session_minutes: 0 }, H);
  await T.post("/api/parent/unlock", { world: "all" }, H);
  const openLevel = async (n) => { await loadProgress(); openWorld("keyboard"); await T.wait(500); [...document.querySelectorAll(".world.level")][n - 1].click(); await T.wait(400); };
  const arrows = { UP: "ArrowUp", DOWN: "ArrowDown", LEFT: "ArrowLeft", RIGHT: "ArrowRight" };
  const cellOf = (emoji) => [...document.querySelectorAll(".garden-cell")].findIndex((c) => c.textContent === emoji);
  const glowing = () => { const g = document.querySelector(".key.goal"); return g && Object.entries({ "↑": "UP", "↓": "DOWN", "←": "LEFT", "→": "RIGHT" }).find(([label]) => label === g.textContent.trim())?.[1]; };
  const delta = { UP: -5, DOWN: 5, LEFT: -1, RIGHT: 1 };                   // one step in the 5-wide garden

  await openLevel(6);
  T.check("the arrow game shows a garden with a bunny and a carrot", cellOf("🐰") >= 0 && cellOf("🥕") >= 0 && cellOf("🐰") !== cellOf("🥕"));
  T.check("only the four arrow keys are drawn", document.querySelectorAll(".keyboard .key").length === 4, document.querySelectorAll(".keyboard .key").length);
  let moves = 0, wrongChecked = false;
  while (glowing() && moves < 20) {
    const want = glowing(), before = cellOf("🐰");
    if (!wrongChecked) {                                                     // a wrong arrow: the bunny stays, the right key pulses
      wrongChecked = true;
      const wrong = Object.keys(arrows).find((k) => k !== want);
      T.key(arrows[wrong]); await T.wait(150);
      T.check("a wrong arrow key does not move the bunny", cellOf("🐰") === before);
      T.check("and the right arrow pulses as a hint", !!document.querySelector(".key.attention"));
    }
    T.key(arrows[want]); await T.wait(150);
    T.check(`the bunny hops ${want.toLowerCase()}`, cellOf("🐰") === before + delta[want], `${before} -> ${cellOf("🐰")}`);
    moves++;
  }
  await T.wait(1500);
  T.check("the bunny reaches the carrot and the level is done", T.name() === "celebrate" && moves >= 4, `${T.name()} after ${moves} moves`);

  await openLevel(7);
  const word = () => document.querySelector(".caps-word").textContent;
  T.check("Caps Lock game starts with small letters and shows one key", word() === "tippy" && document.querySelectorAll(".keyboard .key").length === 1);
  const seen = [];
  for (let i = 0; i < 4; i++) { T.key("CapsLock"); await T.wait(200); seen.push(word()); }
  T.check("each Caps Lock press toggles big and small", seen.join(",") === "TIPPY,tippy,TIPPY,tippy", seen.join(","));
});
