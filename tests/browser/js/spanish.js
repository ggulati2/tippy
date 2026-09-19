// Spanish specifics: the Ñ key, accented letters typed with plain keys, and Free Play pictures for
// words typed without accents.
T.run(async () => {
  await T.wait(1500);
  const H = await T.parentLogin();
  const saved = await fetch("/api/parent/settings", { method: "POST", headers: { "Content-Type": "application/json", ...H },
    body: JSON.stringify({ language: "es", keyboard_layout: "qwerty_es", daily_limit_minutes: 0, session_minutes: 0, child_name: "José" }) }).then((r) => r.json());
  settings = { ...settings, ...saved }; applyLook();
  await T.post("/api/parent/unlock", { world: "all" }, H);

  T.check("the Spanish keyboard has an Ñ key", renderKeyboard().has("Ñ"));
  T.check("Ñ has its own key", keyForChar("ñ") === "Ñ" && keyForChar("Ñ") === "Ñ");
  T.check("accented vowels use the plain vowel key", ["á", "é", "í", "ó", "ú", "ü"].every((c, i) => keyForChar(c) === "AEIOUU"[i]), ["á", "é", "í", "ó", "ú", "ü"].map(keyForChar).join(""));
  T.check("¡ and ¿ are not typed", typingText("¡Hola! ¿Qué tal?") === "Hola Qué tal");
  T.check("a word with Ñ and accents can be typed", isTypable("PIÑA") && isTypable("CAMIÓN") && !isTypable("STRAßE"));
  T.check("the Ñ key has a finger colour", zoneColor("Ñ") !== "#dee2e6");

  // A typing round with accents and Ñ: the child presses the plain key for accents and Ñ for ñ.
  const typed = [];
  typingRound({ screen: "words", icon: "🌳", text: "test", numpad: false, onDone: () => typed.push("done"),
    items: [{ text: "PIÑA", speak: "piña", picture: "🍍" }, { text: "LEÓN", speak: "león", picture: "🦁" }] });
  const presses = [];
  for (let step = 0; step < 40 && !typed.length; step++) {
    const goal = T.goalKey();
    if (goal) { presses.push(goal); T.key(goal); }
    await T.wait(120);
  }
  T.check("the game asks for P I Ñ A, then L E O N", presses.join("").toUpperCase() === "PIÑALEON", presses.join(""));
  T.check("the round finishes", typed.length === 1);

  // Free Play: words typed without accents find their pictures.
  await loadProgress(); openWorld("free"); await T.wait(600);
  const typeWord = async (word) => { for (const c of word) T.key(c); T.key("Enter"); await T.wait(400); };
  const canvasText = () => document.querySelector(".canvas").textContent;
  await typeWord("leon");
  T.check('"leon" (no accent) shows the lion', canvasText().includes("🦁"), canvasText().slice(0, 40));
  await typeWord("piña");
  T.check('"piña" (with the Ñ key) shows the pineapple', canvasText().includes("🍍"), canvasText().slice(0, 40));
  await typeWord("avion");
  T.check('"avion" shows the plane', canvasText().includes("✈"), canvasText().slice(0, 40));
});
