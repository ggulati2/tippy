// Several children: adding and editing them in the parent area, switching, separate progress,
// separate play limits, and the goodnight screen letting a sibling play.
T.run(async () => {
  await T.wait(1500);
  const modal = () => document.querySelector("#modal-root");
  const button = (text) => [...modal().querySelectorAll("button")].find((b) => b.textContent.trim().includes(text));
  const typePin = async (pin) => { for (const d of pin) T.key(d); T.key("Enter"); await T.wait(700); };
  const settingsNow = () => fetch("/api/settings").then((r) => r.json());
  const profiles = () => fetch("/api/profiles").then((r) => r.json());
  const rows = () => [...modal().querySelectorAll(".tab-body .child-row")].filter((r) => r.querySelector(".avatar-select") && r.querySelector("input") && r.querySelector(".seg"));
  const openParent = async () => { document.querySelector("#parent-btn").click(); await T.wait(300); await typePin("2468"); };

  // One child to begin with: no picker, no switch button.
  T.check("with one child there is no switch button", document.querySelector("#who-btn").hidden);
  await openParent();
  button("👧").click(); await T.wait(600);
  T.check("the Children tab lists the one child", rows().length === 1, rows().length);

  // Add "Mia" (German) with the form.
  const form = modal().querySelector(".add-child");
  form.querySelector("input").value = "Mia";
  [...form.querySelectorAll(".seg button")].find((b) => b.textContent === "Deutsch").click();
  [...form.querySelectorAll("button")].find((b) => b.textContent.includes("➕")).click(); await T.wait(800);
  const listing = await profiles();
  T.check("the new child is added", listing.profiles.length === 2 && listing.profiles[1].name === "Mia", JSON.stringify(listing.profiles));
  T.check("the panel lists both children", rows().length === 2, rows().length);
  const mia = listing.profiles[1].id, first = listing.profiles[0].id;

  // Rename and change the picture of the first child.
  const firstRow = rows()[0];
  firstRow.querySelector("input").value = "Ben"; firstRow.querySelector("input").dispatchEvent(new Event("change")); await T.wait(800);
  T.check("renaming works", (await profiles()).profiles[0].name === "Ben");
  const select = rows()[0].querySelector(".avatar-select"); select.value = listing.avatars[5]; select.dispatchEvent(new Event("change")); await T.wait(800);
  T.check("changing the picture works", (await profiles()).profiles[0].avatar === listing.avatars[5]);

  // Mistakes are refused with a message.
  const before = (await profiles()).profiles.length;
  const blank = modal().querySelector(".add-child");
  [...blank.querySelectorAll("button")].find((b) => b.textContent.includes("➕")).click(); await T.wait(300);
  T.check("adding a child without a name is refused", (await profiles()).profiles.length === before && /⚠️/.test(modal().textContent));

  // Look at Mia's data: the parent area now shows Mia, in German.
  [...rows()[1].querySelectorAll(".seg button")][0].click(); await T.wait(800);
  T.check("the parent area title shows the child that is shown", /Mia/.test(modal().querySelector("h2").textContent), modal().querySelector("h2").textContent);
  T.check("Mia's own language (German) is used", /Kinder|Einstellungen/.test(modal().textContent), modal().textContent.slice(0, 80));
  const H = await T.parentLogin();
  await T.post("/api/parent/settings", { daily_limit_minutes: 1 }, H);                 // Mia only
  await T.post("/api/progress/complete", { world: "mouse", level: 1, stars: 3 });      // Mia's progress
  button("Zurück").click(); await T.wait(800);
  T.check("leaving the parent area shows Mia's welcome screen", T.name() === "welcome" && !document.querySelector("#who-btn").hidden);

  // The picker: pick the first child (Ben).
  document.querySelector("#who-btn").click(); await T.wait(600);
  T.check("the who-is-playing screen shows both children", T.name() === "who" && document.querySelectorAll(".child-card").length === 2);
  document.querySelectorAll(".child-card")[0].click(); await T.wait(900);
  const ben = await settingsNow();
  T.check("Ben is playing: English, his own name, no limit", ben.profile_id === first && ben.language === "en" && ben.daily_limit_minutes !== 1 && T.modalCount() === 0, JSON.stringify({ id: ben.profile_id, lang: ben.language, limit: ben.daily_limit_minutes, modals: T.modalCount() }));
  const benProgress = await fetch("/api/progress").then((r) => r.json());
  T.check("Ben has none of Mia's progress", Object.keys(benProgress.worlds.mouse.levels).length === 0);

  // Mia's daily limit is reached: goodnight, and a switch button so Ben can play.
  document.querySelector("#who-btn").click(); await T.wait(500);
  document.querySelectorAll(".child-card")[1].click(); await T.wait(300);
  await T.post("/api/session/heartbeat", { seconds: 60 });
  await refreshLimits(); await T.wait(600);
  T.check("Mia's goodnight screen appears", limitReached && T.modalCount() === 1, modal().textContent.slice(0, 40));
  const switcher = [...modal().querySelectorAll("button")].find((b) => b.textContent.includes("👥"));
  T.check("the goodnight screen offers switching to a sibling", !!switcher);
  switcher.click(); await T.wait(600);
  T.check("the who-is-playing screen opens", T.name() === "who" && T.modalCount() === 0);
  document.querySelectorAll(".child-card")[0].click(); await T.wait(900);
  T.check("Ben can play although Mia's limit is reached", !limitReached && T.modalCount() === 0 && T.name() === "welcome");
  document.querySelector("#who-btn").click(); await T.wait(500);
  document.querySelectorAll(".child-card")[1].click(); await T.wait(900);
  T.check("choosing Mia again shows her goodnight screen", limitReached && T.modalCount() === 1);

  // Remove Ben through the parent area (two steps).
  await T.post("/api/parent/settings", { daily_limit_minutes: 0 }, H);
  await openParent(); await T.wait(300);
  button("👧").click(); await T.wait(600);
  rows()[0].querySelectorAll(".seg button")[1].click(); await T.wait(300);
  T.check("removing asks first", /⚠️/.test(modal().textContent) && (await profiles()).profiles.length === 2);
  [...modal().querySelectorAll(".reset-box button")][0].click(); await T.wait(900);
  T.check("Ben is removed", (await profiles()).profiles.length === 1 && (await profiles()).profiles[0].name === "Mia");
  T.check("the last child has no remove option that works", (await fetch("/api/parent/profiles/" + mia + "/delete", { method: "POST", headers: { "Content-Type": "application/json", ...H }, body: JSON.stringify({ confirm: "DELETE" }) })).status === 422);
});
