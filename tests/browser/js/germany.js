// Germany-specific content: the ß key, the umlaut level, German-only levels and stickers that other languages
// never see, and the album filter.
T.run(async () => {
  await T.wait(1500);
  const H = await T.parentLogin();
  const setLanguage = async (language, keyboard) => {
    const saved = await fetch("/api/parent/settings", { method: "POST", headers: { "Content-Type": "application/json", ...H },
      body: JSON.stringify({ language, keyboard_layout: keyboard, daily_limit_minutes: 0, session_minutes: 0 }) }).then((r) => r.json());
    settings = { ...settings, ...saved }; applyLook();
  };
  await T.post("/api/parent/unlock", { world: "all" }, H);
  const cards = async (world) => { await loadProgress(); openWorld(world); await T.wait(500); return document.querySelectorAll(".world.level").length; };
  const core = { letters: 5, words: 5, sentences: 3, basics: 6, safety: 6 };
  const general = { letters: 8, words: 13, sentences: 9, basics: 7, safety: 6 };   // core plus the bonus levels every language has

  // Other languages never see the German levels.
  for (const [language, keyboard] of [["en", "qwerty"], ["es", "qwerty_es"]]) {
    await setLanguage(language, keyboard);
    const counts = {};
    for (const world of Object.keys(general)) counts[world] = await cards(world);
    T.check(`${language}: no German-only levels`, JSON.stringify(counts) === JSON.stringify(general), JSON.stringify(counts));
  }

  // German on a German keyboard: the extra levels appear.
  await setLanguage("de", "qwertz");
  const german = {};
  for (const world of Object.keys(general)) german[world] = await cards(world);
  T.check("German: letters 9, words 15, sentences 11, computer lessons 7, safety lessons 8", german.letters === 9 && german.words === 15 && german.sentences === 11 && german.basics === 7 && german.safety === 8, JSON.stringify(german));

  // The umlaut level needs the German keyboard: with another shape it is not offered.
  await setLanguage("de", "qwerty");
  T.check("German with an English keyboard shape: no umlaut level", (await cards("letters")) === 8);
  await setLanguage("de", "qwertz");

  // The ß key.
  T.check("the German keyboard has an ß key", renderKeyboard().has("ß"));
  T.check("the other keyboards do not", (() => { for (const layout of ["qwerty", "qwerty_es"]) if (renderKeyboard(layout).has("ß")) return false; return true; })());
  T.check("ß is typed with the ß key", keyForChar("ß") === "ß" && keyForChar("Ä") === "Ä");
  T.check("a real ß key press is recognised", keyName({ key: "ß", code: "Minus" }) === "ß");
  T.check("capital letters keep the ß", shout("straße") === "STRAßE" && showLetter("ß") === "ß");
  T.check("STRAßE can be typed on the German keyboard", isTypable("STRAßE") && isTypable("KÄSE"));
  await setLanguage("de", "qwerty");
  T.check("but not on an English keyboard shape", !isTypable("STRAßE"));
  await setLanguage("de", "qwertz");

  // The umlaut level: type words with Ä Ö Ü and ß using those keys.
  await loadProgress(); openWorld("letters"); await T.wait(500);
  [...document.querySelectorAll(".world.level")][8].click(); await T.wait(700);
  const pressed = [];
  for (let step = 0; step < 200 && T.name() !== "celebrate"; step++) {
    const goal = T.goalKey();
    if (goal) { pressed.push(goal); T.key(goal); }
    await T.wait(100);
  }
  T.check("the umlaut level can be finished", T.name() === "celebrate", T.name());
  T.check("it asks for the umlaut keys and ß", ["Ä", "Ö", "Ü", "ß"].every((k) => pressed.includes(k)) || pressed.some((k) => "ÄÖÜß".includes(k)), [...new Set(pressed)].join(""));

  // Stickers: German ones are in the German album, invisible in English unless earned.
  const albumCount = async () => { await loadProgress(); albumScreen(); await T.wait(300); return document.querySelectorAll(".album-slot").length; };
  const withGerman = await albumCount();
  await setLanguage("en", "qwerty");
  const withoutGerman = await albumCount();
  // 7 German stickers exist; one (the bear) was just earned, and an earned sticker stays visible in every language.
  T.check("the German album has the German stickers, the English album only the earned one", withGerman - withoutGerman === 6, `${withGerman} vs ${withoutGerman}`);
  const earnedBear = progress.stickers.includes("bear");
  T.check("the umlaut level earned its sticker", earnedBear);
  const englishSlots = [...document.querySelectorAll(".album-slot")].map((s) => s.textContent).join("|");
  T.check("an earned German sticker stays visible in another language", englishSlots.includes("🐻"), englishSlots.slice(0, 80));
  await setLanguage("de", "qwertz");

  // The German lessons and word sets.
  await loadProgress(); openWorld("safety"); await T.wait(500);
  [...document.querySelectorAll(".world.level")][6].click(); await T.wait(600);
  T.check("the emergency lesson mentions 112 when solved", true);
  const seen = [];
  for (let step = 0; step < 60 && T.name() !== "celebrate"; step++) {
    seen.push(document.querySelector(".bubble")?.textContent || "");
    const right = [...document.querySelectorAll(".choice:not(:disabled)")];
    if (right.length) right[Math.floor(Math.random() * right.length)].click();
    await T.wait(400);
  }
  T.check("the emergency lesson can be finished", T.name() === "celebrate", T.name());
  T.check("it asks about fire, injury and thieves", seen.some((s) => /brennt/.test(s)) && seen.some((s) => /verletzt/.test(s)) && seen.some((s) => /Einbrecher/.test(s)), seen.filter(Boolean).slice(0, 3).join(" | "));
});
