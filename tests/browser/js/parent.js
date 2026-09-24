// The parent area: PIN entry, every tab and setting, changing the PIN, backup, reset and exit.
T.run(async () => {
  await T.wait(1500);
  const modal = () => document.querySelector("#modal-root");
  const mtext = () => modal().textContent;
  const typePin = async (pin, enter = true) => { for (const d of pin) T.key(d); if (enter) T.key("Enter"); await T.wait(700); };
  const button = (text) => [...modal().querySelectorAll("button")].find((b) => b.textContent.trim().includes(text));
  const body = () => modal().querySelector(".tab-body");
  const settingsNow = () => fetch("/api/settings").then((r) => r.json());
  const fits = (label) => {
    const p = modal().querySelector(".panel"); if (!p) return;
    const r = p.getBoundingClientRect();
    T.check("the panel fits the window: " + label, r.top >= -1 && r.bottom <= innerHeight + 1 && r.right <= innerWidth + 1, `${Math.round(r.top)}..${Math.round(r.bottom)} of ${innerHeight}`);
  };
  const segment = (label, text) => {
    const row = [...body().querySelectorAll(".row")].find((r) => r.textContent.includes(label));
    return row && [...row.querySelectorAll("button")].find((b) => b.textContent.trim() === text);
  };
  const choose = async (label, text) => {
    const b = segment(label, text);
    if (!b) { T.check(`control "${label}" -> "${text}" exists`, false); return; }
    b.click(); await T.wait(600);
  };

  // A wrong PIN, then the right one.
  document.querySelector("#parent-btn").click(); await T.wait(300);
  await typePin("9999");
  T.check("a wrong PIN keeps the PIN pad open with a message", !!modal().querySelector(".keypad") && !modal().querySelector(".tabs"), mtext().slice(0, 60));
  await typePin("2468");
  T.check("the right PIN opens the parent area", !!modal().querySelector(".tabs"));
  fits("progress tab");

  // Progress tab.
  T.check("charts and heat map are drawn", !!body().querySelector(".heat") && body().querySelectorAll("svg").length >= 1);
  const details = body().querySelectorAll("details");
  T.check("every chart has a 'show as table' option", details.length >= 2, "count " + details.length);

  // Settings tab.
  button("⚙️").click(); await T.wait(500);
  fits("settings tab");
  await choose("Text size", "A++");
  T.check("text size is saved and applied", (await settingsNow()).font_scale === 1.25 && getComputedStyle(document.documentElement).getPropertyValue("--font-scale").trim() === "1.25");
  await choose("Text size", "A");
  await choose("Animations", "Off");
  T.check("animations off is saved and applied", (await settingsNow()).reduce_motion === true && document.body.classList.contains("reduce-motion"));
  await choose("Animations", "On");
  await choose("Voice", "Off"); T.check("voice off", (await settingsNow()).voice_on === false); await choose("Voice", "On");
  await choose("Sounds", "Off"); T.check("sounds off", (await settingsNow()).sound_on === false); await choose("Sounds", "On");
  await choose("Letters", "abc"); T.check("lowercase letters", (await settingsNow()).letter_case === "lower"); await choose("Letters", "ABC");
  await choose("Keyboard shape", "QWERTZ"); T.check("QWERTZ layout", (await settingsNow()).keyboard_layout === "qwertz"); await choose("Keyboard shape", "QWERTY");
  await choose("Suggest a break after", "15 min"); T.check("break length", (await settingsNow()).session_minutes === 15); await choose("Suggest a break after", "10 min");
  await choose("Daily play limit", "45 min"); T.check("daily limit 45", (await settingsNow()).daily_limit_minutes === 45);
  await choose("Daily play limit", "Off"); T.check("daily limit off", (await settingsNow()).daily_limit_minutes === 0);
  await choose("Ask Tippy", "On"); T.check("Ask Tippy on", (await settingsNow()).ask_tippy === true);
  const answer = (await fetch("/api/ask?topic=wifi").then((r) => r.json())).text;
  T.check("Ask Tippy answers a picture question", !!answer, String(answer).slice(0, 50));
  await choose("Ask Tippy", "Off"); T.check("Ask Tippy off again", (await settingsNow()).ask_tippy === false);
  const interests = [...body().querySelectorAll(".row")].find((r) => r.textContent.includes("Interests"));
  T.check("four interest buttons", interests.querySelectorAll("button").length === 4);

  // Names: accents work, markup is refused (and the old name stays).
  const inputs = () => [...body().querySelectorAll("input.text-input")];
  inputs()[0].value = "Zoë Ünal"; inputs()[0].dispatchEvent(new Event("change")); await T.wait(600);
  T.check("a name with accents is saved", (await settingsNow()).child_name === "Zoë Ünal", (await settingsNow()).child_name);
  inputs()[1].value = "Dino"; inputs()[1].dispatchEvent(new Event("change")); await T.wait(600);
  T.check("favourite word is saved", (await settingsNow()).favorite_word === "Dino");
  inputs()[0].value = "<b>x</b>"; inputs()[0].dispatchEvent(new Event("change")); await T.wait(600);
  T.check("a name with HTML is refused", (await settingsNow()).child_name === "Zoë Ünal", (await settingsNow()).child_name);

  // Language switch: every label is translated.
  await choose("Language", "Deutsch");
  T.check("the parent area switches to German", /Einstellungen|Sprache|Textgröße/.test(mtext()), mtext().slice(0, 60));
  fits("settings tab (German)");
  const labels = [...body().querySelectorAll(".row")].map((r) => r.firstChild.textContent).join(" | ");
  T.check("no untranslated label keys are visible", !/set[A-Z]|setup\./.test(labels), labels.slice(0, 120));
  await choose("Sprache", "English");

  // Unlock everything.
  (button("Unlock all") || button("🔓 Unlock")).click(); await T.wait(600);
  const progress = await fetch("/api/progress").then((r) => r.json());
  T.check("unlock all opens every world", Object.values(progress.worlds).every((w) => w.unlocked));

  // Data tab: backup and reset.
  button("🗄️").click(); await T.wait(500);
  fits("data tab");
  T.check("the data tab shows the licence (everything unlocked on the test server)", /developer|Entwickler|desarrollo/.test(modal().querySelector(".licence-status").textContent));
  let downloads = 0; const realClick = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () { downloads++; T.check("the backup is a JSON download", this.download.endsWith(".json") && this.href.startsWith("blob:"), this.download); };
  button("💾").click(); await T.wait(600);
  HTMLAnchorElement.prototype.click = realClick;
  T.check("the backup button produced a download", downloads === 1);
  const H = await T.parentLogin();
  const backup = JSON.stringify(await fetch("/api/parent/export", { headers: H }).then((r) => r.json()));
  T.check("the backup contains no PIN hash, key or summary", !/pin_hash|sk-or|weekly_summary/.test(backup));
  button("🗑️").click(); await T.wait(300);
  T.check("reset asks for confirmation", mtext().includes("⚠️"));
  [...modal().querySelectorAll(".reset-box button")].pop().click(); await T.wait(200);
  T.check("cancelling leaves the data alone", !modal().querySelector(".reset-box").textContent.includes("⚠️"));
  await T.post("/api/progress/complete", { world: "mouse", level: 1, stars: 3 });   // something to lose
  button("🗑️").click(); await T.wait(300);
  modal().querySelector(".pin-confirm").value = "0000";
  [...modal().querySelectorAll(".reset-box button")][0].click(); await T.wait(600);
  T.check("a wrong PIN deletes nothing", (await fetch("/api/progress").then((r) => r.json())).stickers.length > 0 && mtext().includes("⚠️"));
  modal().querySelector(".pin-confirm").value = "2468";
  [...modal().querySelectorAll(".reset-box button")][0].click(); await T.wait(800);
  const after = await fetch("/api/progress").then((r) => r.json());
  T.check("reset clears stickers", after.stickers.length === 0);
  const kept = await settingsNow();
  T.check("reset keeps the settings and the PIN", kept.child_name === "Zoë Ünal" && !kept.setup_needed);

  // Delete everything asks for the PIN too; a wrong one leaves everything as it was (a right one would reload the page).
  button("🧨").click(); await T.wait(300);
  T.check("delete everything asks first", !!modal().querySelector(".erase-box .pin-confirm"));
  modal().querySelector(".erase-box .pin-confirm").value = "1111";
  modal().querySelector(".erase-box .exit-btn").click(); await T.wait(600);
  T.check("delete everything with a wrong PIN deletes nothing", !(await settingsNow()).setup_needed && (await settingsNow()).child_name === "Zoë Ünal");

  // Datenschutz: the same text as docs/PRIVACY.md.
  button("🛡️").click(); await T.wait(400);
  T.check("the privacy tab shows the privacy text", modal().querySelectorAll(".privacy-text h3").length >= 4 && modal().querySelectorAll(".privacy-text li").length >= 6);
  fits("privacy tab");

  // Printables: the keyboard sheet is drawn into #print-root and the browser's print dialog is opened.
  let printed = 0; const realPrint = window.print; window.print = () => { printed++; };
  button("📊").click(); await T.wait(600);
  T.check("the progress tab offers printables", !!modal().querySelector(".print-card .print-sheet"));
  modal().querySelector(".print-sheet").click(); await T.wait(200);
  T.check("the keyboard sheet is printed with every letter key", printed === 1 && document.querySelectorAll("#print-root .sheet-key").length >= 26);
  window.print = realPrint;

  // Change the PIN.
  button("⚙️").click(); await T.wait(500);
  button("🔑").click(); await T.wait(400);
  T.check("change PIN shows the number pad", !!modal().querySelector(".keypad"));
  await typePin("123");
  T.check("a PIN with fewer than 4 digits is refused", /4/.test(mtext()), mtext().slice(0, 60));
  await typePin("7531"); await typePin("7531");
  T.check("after changing the PIN the parent is signed out", !!modal().querySelector(".keypad") && !modal().querySelector(".tabs"));
  await typePin("2468");
  T.check("the old PIN no longer works", !modal().querySelector(".tabs"));
  await typePin("7531");
  T.check("the new PIN works", !!modal().querySelector(".tabs"));
  button("⚙️").click(); await T.wait(400); button("🔑").click(); await T.wait(300);
  await typePin("1111"); await typePin("2222");
  T.check("two different PINs start over with a message", !!modal().querySelector(".keypad") && /different|verschieden/i.test(mtext()), mtext().slice(0, 60));
  T.key("Escape"); await T.wait(300);
  T.check("Escape closes the PIN pop-up", !modal().querySelector(".keypad"));

  // Leaving and exiting.
  document.querySelector("#parent-btn").click(); await T.wait(300); await typePin("7531");
  button("Back").click(); await T.wait(600);
  T.check("Back leaves the parent area", modal().children.length === 0 && T.name() === "welcome");
  document.querySelector("#parent-btn").click(); await T.wait(300); await typePin("7531");
  button("Exit").click(); await T.wait(1000);
  T.check("Exit shows the goodbye screen", T.name() === "bye");
});
