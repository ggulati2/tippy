// Break suggestion, daily limit and how a child cannot get around it. Time is simulated.
T.run(async () => {
  await T.wait(1500);
  const H = await T.parentLogin();
  const modalText = () => document.querySelector("#modal-root")?.textContent.trim() || "";

  // Break after the session length (10 minutes of play; we jump the counter to just before).
  await T.post("/api/parent/settings", { session_minutes: 10, daily_limit_minutes: 0 }, H);
  await refreshLimits();
  document.querySelector(".play-btn").click(); await T.wait(500);
  sessionSeconds = 598;
  for (let i = 0; i < 6; i++) { document.dispatchEvent(new Event("pointermove")); await T.wait(1000); }
  T.check("a break is suggested after the session length", T.modalCount() === 1 && breakShown);
  [...document.querySelectorAll("#modal-root .choice")][1].click(); await T.wait(300);      // "keep playing"
  T.check("'keep playing' closes the pop-up and gives about 5 more minutes", T.modalCount() === 0 && sessionSeconds === 300, "session seconds " + sessionSeconds);
  sessionSeconds = 599; breakShown = false;
  for (let i = 0; i < 4; i++) { document.dispatchEvent(new Event("pointermove")); await T.wait(1000); }
  [...document.querySelectorAll("#modal-root .choice")][0].click(); await T.wait(500);       // "take a break"
  T.check("taking the break opens the screen-break lesson", T.name() === "basics-4", T.name());

  // A child who walked away does not use up play time.
  const before = sessionSeconds; lastActivity = Date.now() - 60000; await T.wait(3000);
  T.check("idle time is not counted", sessionSeconds === before);

  // Daily limit.
  await T.post("/api/parent/settings", { daily_limit_minutes: 1 }, H);
  const hb = await T.post("/api/session/heartbeat", { seconds: 60 });
  T.check("the server reports the daily limit as reached", hb.daily_reached === true, JSON.stringify(hb));
  await refreshLimits(); await T.wait(300);
  T.check("the goodnight screen appears", limitReached && T.modalCount() === 1, modalText().slice(0, 40));
  T.key("Escape"); T.key("Enter"); T.key(" "); document.querySelector("#home-btn").click(); document.querySelector("#screen button")?.click(); await T.wait(500);
  T.check("Escape, Enter, Space, Home and clicking cannot get past it", T.modalCount() === 1 && limitReached);

  // Only the parent lifts it.
  document.querySelector("#parent-btn").click(); await T.wait(300);
  for (const d of "2468") T.key(d);
  T.key("Enter"); await T.wait(600);
  T.check("the PIN opens the parent area over the goodnight screen", !!document.querySelector("#modal-root .tabs"));
  await T.post("/api/parent/settings", { daily_limit_minutes: 0 }, H);
  [...document.querySelectorAll("#modal-root .panel-actions button")].pop().click(); await T.wait(800);
  T.check("after the parent lifts the limit, Tippy is usable again", T.modalCount() === 0 && !limitReached && T.name() === "welcome", `modals ${T.modalCount()} reached ${limitReached} screen ${T.name()}`);

  // The goodnight screen goes away by itself when the limit stops applying (for example at midnight).
  await T.post("/api/parent/settings", { daily_limit_minutes: 1 }, H);
  await refreshLimits(); await T.wait(300);
  T.check("limit applies again", limitReached && T.modalCount() === 1);
  await T.post("/api/parent/settings", { daily_limit_minutes: 90 }, H);
  await T.wait(61000);
  T.check("goodnight screen clears by itself when the limit no longer applies", T.modalCount() === 0 && !limitReached);
});
