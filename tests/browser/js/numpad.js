// The number pad rule: when the parent says "this computer has a number pad", Number Land asks for the
// pad keys and gives the row of digits a friendly hint; otherwise both work. Real key events carry a
// `code` ("Numpad3" for the pad, "Digit3" for the row above the letters), so the test sends both.
T.run(async () => {
  await T.wait(1500);
  const H = await T.parentLogin();
  await T.post("/api/parent/settings", { daily_limit_minutes: 0, session_minutes: 0 }, H);
  await T.post("/api/parent/unlock", { world: "all" }, H);
  const press = (digit, code) => document.dispatchEvent(new KeyboardEvent("keydown", { key: digit, code, bubbles: true, cancelable: true }));
  const filled = () => document.querySelector(".dots").textContent.split("●").length - 1;
  const openLevel = async (n) => { await loadProgress(); openWorld("numbers"); await T.wait(500); [...document.querySelectorAll(".world.level")][n - 1].click(); await T.wait(400); };
  const target = () => document.querySelector("#screen").dataset.answer || T.goalKey();

  // No number pad announced: the row of digits works, and so does the pad.
  await openLevel(1);
  press(target(), "Digit" + target());
  await T.wait(200);
  T.check("without the setting, the digit row works", filled() === 1, filled());
  await T.wait(900);
  press(target(), "Numpad" + target());
  await T.wait(200);
  T.check("without the setting, the number pad works", filled() === 2, filled());

  // This computer has a number pad: the digit row gets a hint, the pad works.
  await T.post("/api/parent/settings", { has_numpad: true }, H);
  await reloadSettings();
  T.check("the setting reaches the page", settings.has_numpad === true);
  await openLevel(1);
  await T.wait(900);
  const d = target();
  press(d, "Digit" + d);
  await T.wait(200);
  T.check("with the setting, the digit row is not accepted", filled() === 0, filled());
  T.check("the right pad key pulses as a hint", !!document.querySelector(".key.attention"));
  press(d, "Numpad" + d);
  await T.wait(200);
  T.check("with the setting, the number pad works", filled() === 1, filled());

  // The same rule in a typing game (numbers in order).
  await openLevel(3);
  const first = T.goalKey();
  press(first, "Digit" + first); await T.wait(200);
  T.check("typing games follow the rule too (digit row ignored)", document.querySelectorAll(".slot.typed").length === 0);
  press(first, "Numpad" + first); await T.wait(200);
  T.check("typing games accept the pad", document.querySelectorAll(".slot.typed").length === 1);

  // Letters and other screens are not affected.
  openWorld("letters"); await T.wait(400); [...document.querySelectorAll(".world.level")][0].click(); await T.wait(400);
  const letter = T.goalKey();
  document.dispatchEvent(new KeyboardEvent("keydown", { key: letter, code: "Key" + letter, bubbles: true })); await T.wait(300);
  T.check("Letter Land is not affected by the setting", document.querySelector(".dots").textContent.startsWith("●"));

  // The parent's heat map shows the number pad once digits were practised.
  await T.post("/api/parent/settings", { has_numpad: false }, H);
  await reloadSettings();
  document.querySelector("#parent-btn").click(); await T.wait(300);
  for (const d of "2468") T.key(d);
  T.key("Enter"); await T.wait(900);
  const heat = document.querySelectorAll("#modal-root .keyboard.heat");
  T.check("the heat map has a second board for the number pad", heat.length === 2 && heat[1].classList.contains("numpad"), heat.length);
  const keysDrawn = [...(heat[1] ? heat[1].querySelectorAll(".key") : [])].map((k) => k.textContent).join("");
  T.check("the number pad heat map shows all digits", /0/.test(keysDrawn) && /9/.test(keysDrawn), keysDrawn);
});
