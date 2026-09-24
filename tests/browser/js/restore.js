// Backup and restore through the real screens: save, wipe, restore, restore as a new child,
// and refuse files that are not backups.
T.run(async () => {
  await T.wait(1500);
  const modal = () => document.querySelector("#modal-root");
  const button = (text) => [...modal().querySelectorAll("button")].find((b) => b.textContent.trim().includes(text));
  const typePin = async (pin) => { for (const d of pin) T.key(d); T.key("Enter"); await T.wait(700); };
  const progress = () => fetch("/api/progress").then((r) => r.json());
  const levelCount = (p) => Object.values(p.worlds).reduce((n, w) => n + Object.keys(w.levels).length, 0);
  const H = await T.parentLogin();
  const send = (file) => {                                     // like choosing a file in the file dialog
    const input = modal().querySelector('input[type="file"]');
    const transfer = new DataTransfer(); transfer.items.add(file);
    input.files = transfer.files;
    input.dispatchEvent(new Event("change"));
    // The answer is either a question box or a message; wait for whichever appears.
    const box = modal().querySelector(".restore-box"), message = modal().querySelector(".llm-result");
    const before = message.textContent;
    return T.until(() => box.children.length > 0 || message.textContent !== before);
  };

  // A child with some history, and its backup.
  for (const [world, level] of [["mouse", 1], ["mouse", 2], ["mouse", 3], ["keyboard", 1]]) await T.post("/api/progress/complete", { world, level, stars: 3 });
  await T.post("/api/parent/settings", { child_name: "Mia", daily_limit_minutes: 45 }, H);
  const before = await progress();
  const backupText = JSON.stringify(await fetch("/api/parent/export", { headers: H }).then((r) => r.json()));
  T.check("the child has progress to back up", levelCount(before) === 4 && before.stickers.length > 0, levelCount(before) + " levels");

  // Wipe it (Data tab, reset).
  document.querySelector("#parent-btn").click(); await T.wait(300); await typePin("2468");
  button("🗄️").click(); await T.wait(500);
  button("🗑️").click(); await T.wait(300);
  modal().querySelector(".pin-confirm").value = "2468";
  [...modal().querySelectorAll(".reset-box:not(.restore-box) button")][0].click(); await T.wait(800);
  T.check("reset empties the progress", levelCount(await progress()) === 0);

  // Restore into the same child.
  T.check("there is a restore button", !!button("📂"));
  await send(new File([backupText], "tippy-backup.json", { type: "application/json" }));
  T.check("choosing a file asks before replacing anything", /⚠️/.test(modal().querySelector(".restore-box").textContent) && levelCount(await progress()) === 0, `box="${modal().querySelector(".restore-box").textContent.slice(0, 60)}" levels=${levelCount(await progress())} modal=${modal().textContent.slice(-150)}`);
  [...modal().querySelectorAll(".restore-box button")].pop().click(); await T.wait(300);      // Cancel
  T.check("cancel changes nothing", levelCount(await progress()) === 0 && modal().querySelector(".restore-box").children.length === 0);
  await send(new File([backupText], "tippy-backup.json", { type: "application/json" }));
  [...modal().querySelectorAll(".restore-box button")][0].click(); await T.until(() => /Restored:/.test(modal().textContent));       // Replace
  const after = await progress();
  T.check("the restore brings the levels and stickers back", levelCount(after) === 4 && after.stickers.length === before.stickers.length, `${levelCount(after)} levels, ${after.stickers.length} stickers`);
  T.check("the restore shows a confirmation", /✓/.test(modal().textContent) && /4 levels/.test(modal().textContent), modal().textContent.slice(-120));
  const settings1 = await fetch("/api/settings").then((r) => r.json());
  T.check("the settings came back too", settings1.child_name === "Mia" && settings1.daily_limit_minutes === 45);

  // Restore as a new child: the first child keeps its data, the new one gets a copy.
  button("🗄️").click(); await T.wait(500);
  await send(new File([backupText], "tippy-backup.json", { type: "application/json" }));
  [...modal().querySelectorAll(".restore-box button")][1].click(); await T.until(() => /Restored:/.test(modal().textContent));       // Add as a new child
  const listing = await fetch("/api/profiles").then((r) => r.json());
  T.check("a new child was added from the backup", listing.profiles.length === 2 && listing.profiles[1].name === "Mia", JSON.stringify(listing.profiles));
  T.check("the parent area still shows the first child", (await fetch("/api/settings").then((r) => r.json())).profile_id === listing.profiles[0].id);
  await T.post("/api/profiles/select", { id: listing.profiles[1].id });
  T.check("the new child has the restored progress", levelCount(await progress()) === 4);
  await T.post("/api/profiles/select", { id: listing.profiles[0].id });

  // Files that must be refused.
  button("🗄️").click(); await T.wait(500);
  const bad = async (label, file, expected) => {
    await send(file); await T.wait(300);
    const box = modal().querySelector(".restore-box");
    if (box && box.children.length) { [...box.querySelectorAll("button")][0].click(); await T.until(() => box.children.length === 0); }   // if it asks, go ahead: the server must refuse
    await T.wait(300);
    T.check(label, expected.test(modal().textContent) && levelCount(await progress()) === 4, modal().textContent.slice(-100));
  };
  await bad("text that is not JSON is refused", new File(["hello, this is not json"], "x.json"), /not a Tippy backup/);
  await bad("JSON that is not a Tippy backup is refused", new File([JSON.stringify({ app: "other", tables: {} })], "x.json"), /not a Tippy backup/);
  await bad("a file that is too big is refused", new File(["x".repeat(5 * 1024 * 1024 + 10)], "big.json"), /too big/);

  // A hostile file: tries to set the PIN and the helper model, and to add nonsense.
  const hostile = JSON.stringify({ app: "tippy", tables: {
    settings: [{ key: "pin_hash", value: "aa:bb" }, { key: "openrouter_model", value: "evil/model" }, { key: "child_name", value: "<img src=x onerror=alert(1)>" }],
    progress: [{ world: "mouse", level: 1, status: "done", stars: 3 }, { world: "x'); DROP TABLE progress;--", level: 1, status: "done", stars: 1 }] } });
  await send(new File([hostile], "hostile.json"));
  [...modal().querySelectorAll(".restore-box button")][0].click(); await T.until(() => /Restored:/.test(modal().textContent));
  const verify = await fetch("/api/parent/verify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pin: "2468" }) });
  T.check("a hostile backup cannot change the PIN", verify.status === 200);
  const status = await fetch("/api/parent/status", { headers: H }).then((r) => r.json());
  T.check("a hostile backup cannot change the helper model", status.model !== "evil/model", status.model);
  const now = await fetch("/api/settings").then((r) => r.json());
  T.check("markup in a name is refused", now.child_name === "Mia", now.child_name);
  T.check("only the valid row was restored", levelCount(await progress()) === 1);
});
