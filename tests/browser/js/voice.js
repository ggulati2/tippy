// Tippy's recorded voice: known sentences are played from the recordings, a line with the child's name is played in pieces,
// and anything without a recording falls back to the computer's voice. (Audio is replaced by a spy: no sound in tests.)
T.run(async () => {
  await T.wait(1500);
  const H = await T.parentLogin();
  await T.post("/api/parent/settings", { language: "en", voice_on: true, child_name: "Mia", daily_limit_minutes: 0, session_minutes: 0 }, H);
  settings = { ...settings, language: "en", voice_on: true, child_name: "Mia" }; applyLook(); await voice.loading;
  T.check("the English recordings are loaded", voice.clips.size > 500, voice.clips.size + " clips");

  const played = [], ended = [];
  window.Audio = function (src) {
    this.src = src; this.paused = false; this.ended = false; this.pause = () => { this.paused = true; };
    this.addEventListener = (type, fn) => { if (type === "ended") ended.push(() => { this.ended = true; fn(); }); };
    this.play = () => { played.push(src); return Promise.resolve(); };
  };
  const said = [], realSpeak = window.speechSynthesis && speechSynthesis.speak;
  window.speakWithSystemVoice = (text) => said.push(text);          // what the computer's voice would have said
  const reset = () => { played.length = 0; ended.length = 0; said.length = 0; };

  reset(); speak(t("play"));
  T.check("a known text is played from its recording", played.length === 1 && played[0] === `voice/en/${voiceKey(t("play"))}.ogg` && said.length === 0, JSON.stringify({ played, said }));

  reset(); speak("Zebra crossing quokka");
  T.check("an unknown text uses the computer's voice", played.length === 0 && said[0] === "Zebra crossing quokka", JSON.stringify({ played, said }));

  reset(); speak("Hi Mia! Let's play!");
  T.check("a line with the name starts with the recorded greeting", played.length === 1 && played[0].endsWith(voiceKey("Hi") + ".ogg"), JSON.stringify(played));
  ended.shift()();
  T.check("then the name is said by the computer's voice", said.length === 1 && said[0] === "Mia", JSON.stringify(said));
  // (the system voice would call next() when it has finished; here we call it by hand through the same path)
  reset(); muted = true; speak(t("play"));
  T.check("muted: nothing is said", played.length === 0 && said.length === 0);
  muted = false;

  reset(); speak(t("play")); setScreen("x", el("div", {}, "x"));
  ended.forEach((fn) => fn());
  T.check("a new screen stops the old recording (nothing follows it)", played.length === 1 && said.length === 0);

  // Owner's bug report: after a typed sentence the round must wait until the whole sentence has been read aloud.
  // (later() waits for Tippy in every world; the typing round is the case that was seen.)
  reset(); let finished = false;
  typingRound({ screen: "t", icon: "", text: "", items: [{ text: "A", speak: t("play") }], onDone: () => { finished = true; } });
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "a", code: "KeyA" }));
  await T.wait(2500);
  T.check("a typing round waits while the sentence is still being read", played.length === 1 && !finished, JSON.stringify({ played, finished }));
  ended.shift()(); await T.wait(600);
  T.check("and moves on once it has been read", finished);

  // The same holds for every world: a timed step waits for Tippy, but runs at once when Tippy is quiet.
  reset(); setScreen("x", el("div", {}, "x")); let stepped = 0;
  speak(t("play")); later(() => stepped++, 100); await T.wait(700);
  T.check("a timed step waits while Tippy is talking", stepped === 0);
  ended.shift()(); await T.wait(600);
  T.check("and runs once Tippy has finished", stepped === 1);
  later(() => stepped++, 100); await T.wait(250);
  T.check("with Tippy quiet it runs on time", stepped === 2);

  reset(); settings.language = "de"; speak(t("play"));
  T.check("a language without recordings uses the computer's voice", played.length === 0, JSON.stringify(played));
});
