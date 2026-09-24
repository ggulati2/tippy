// The first-run wizard on a brand-new install: choose a language (three are offered), choose a PIN
// (twice), the child's name and a daily limit, then Tippy starts in that language.
T.run(async () => {
  await T.wait(1500);
  const lang = location.hash.slice(1) || "es";
  const modal = () => document.querySelector("#modal-root");
  const button = (text) => [...modal().querySelectorAll("button")].find((b) => b.textContent.trim().includes(text));
  const digits = async (pin) => { for (const d of pin) T.key(d); T.key("Enter"); await T.wait(600); };

  T.check("the wizard opens on a new install", T.modalCount() === 1 && /Welcome/.test(modal().textContent), modal().textContent.slice(0, 60));
  const choices = [...modal().querySelectorAll(".choices button")].map((b) => b.textContent);
  T.check("every language is offered by its own name", ["English", "Deutsch", "Español"].every((n) => choices.includes(n)), choices.join(","));
  const native = { en: "English", de: "Deutsch", es: "Español" }[lang];
  button(native).click(); await T.wait(500);
  T.check("the next step asks: at home or in a classroom", !!modal().querySelector(".place-home") && !!modal().querySelector(".place-class"));
  modal().querySelector(".place-home").click(); await T.wait(500);
  T.check("the PIN step is shown in the chosen language", modal().querySelector("h2").textContent.length > 3 && modal().querySelector(".keypad"), modal().querySelector("h2").textContent);
  await digits("2468"); await digits("2468");
  const basics = modal().textContent;
  T.check("the last step is shown in the chosen language", { en: /Almost ready/, de: /Gleich geschafft/, es: /Casi listo/ }[lang].test(basics), basics.slice(0, 60));
  const name = modal().querySelector("input");
  name.value = { en: "Mia", de: "Jürgen", es: "José" }[lang]; name.dispatchEvent(new Event("change"));
  [...modal().querySelectorAll(".seg button")].find((b) => /45/.test(b.textContent)).click(); await T.wait(300);
  [...modal().querySelectorAll("button")].find((b) => b.classList.contains("play-btn")).click(); await T.wait(1200);
  const settingsNow = await fetch("/api/settings").then((r) => r.json());
  T.check("the choices were saved", settingsNow.language === lang && settingsNow.daily_limit_minutes === 45 && settingsNow.child_name.length > 2 && !settingsNow.setup_needed, JSON.stringify(settingsNow));
  T.check("the keyboard shape matches the language", settingsNow.keyboard_layout === LANGUAGES.find((l) => l.code === lang).keyboard, settingsNow.keyboard_layout);
  T.check("Tippy starts on the welcome screen in that language", T.name() === "welcome" && document.querySelector(".play-btn").textContent.includes({ en: "Play", de: "Spielen", es: "Jugar" }[lang]), document.querySelector(".play-btn")?.textContent);
  T.check("the voice tag is right", voiceTag() === { en: "en-US", de: "de-DE", es: "es-ES" }[lang], voiceTag());
});
