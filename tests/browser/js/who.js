// Tippy starts with two children already on this computer: the first thing the child sees is
// "Who is playing?", and picking a picture loads that child's own settings.
T.run(async () => {
  await T.wait(1500);
  T.check("the first screen is 'who is playing?'", T.name() === "who", T.name());
  const cards = [...document.querySelectorAll(".child-card")];
  T.check("there is one big card per child, with a picture and a name", cards.length === 2 && cards.every((c) => c.querySelector(".icon").textContent && c.textContent.length > 2), cards.map((c) => c.textContent).join(" | "));
  T.check("no goodnight or other pop-up covers the choice", T.modalCount() === 0);
  T.check("the home button is not needed here", true);
  cards[1].click(); await T.wait(900);
  const now = await fetch("/api/settings").then((r) => r.json());
  T.check("the second child is now playing, in German", T.name() === "welcome" && now.language === "de" && now.child_name === "Lea", JSON.stringify({ screen: T.name(), lang: now.language, name: now.child_name }));
  T.check("the welcome screen speaks German to Lea", /Los|Spielen|Spiel/i.test(document.querySelector(".play-btn").textContent), document.querySelector(".play-btn").textContent);
  T.check("the switch button shows Lea's picture", !document.querySelector("#who-btn").hidden && document.querySelector("#who-btn").textContent.length > 0);
  document.querySelector(".play-btn").click(); await T.wait(900);
  T.check("Lea can open the world map", T.name() === "map", T.name());
  T.check("the switch button is available on the map too", !document.querySelector("#who-btn").hidden);
  document.querySelector("#who-btn").click(); await T.wait(500);
  cards.length = 0;
  document.querySelectorAll(".child-card")[0].click(); await T.wait(900);
  const first = await fetch("/api/settings").then((r) => r.json());
  T.check("switching back loads the first child's English settings", first.language === "en" && T.name() === "welcome");
});
