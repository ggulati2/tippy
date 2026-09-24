// Classroom mode on a brand-new install (docs/REVAMP_BRIEF.md section 6.5): the teacher setup, an anonymous class
// of 25 told apart by pictures, the class overview with its CSV file, and the limit of 30 children.
T.run(async () => {
  await T.wait(1500);
  const modal = () => document.querySelector("#modal-root");
  const button = (text) => [...modal().querySelectorAll("button")].find((b) => b.textContent.trim().includes(text));
  const digits = async (pin) => { for (const d of pin) T.key(d); T.key("Enter"); await T.wait(600); };

  button("Deutsch").click(); await T.wait(500);
  modal().querySelector(".place-class").click(); await T.wait(500);
  T.check("the classroom asks for a teacher PIN", /Lehrkraft/.test(modal().querySelector("h2").textContent), modal().querySelector("h2").textContent);
  await digits("2468"); await digits("2468");
  [...modal().querySelectorAll(".seg button")].find((b) => b.textContent.trim() === "25").click(); await T.wait(300);
  [...modal().querySelectorAll(".seg button")].find((b) => b.textContent.trim() === "An").click(); await T.wait(300);
  modal().querySelector(".play-btn").click(); await T.wait(1500);

  const s = await fetch("/api/settings").then((r) => r.json());
  T.check("the class was made", s.classroom === true && s.profile_count === 25 && !s.setup_needed, JSON.stringify({ c: s.classroom, n: s.profile_count }));
  T.check("the class starts on 'who is playing?'", T.name() === "who", T.name());
  const cards = [...document.querySelectorAll(".child-card")];
  T.check("25 picture cards, all different, no names", cards.length === 25 && new Set(cards.map((c) => c.querySelector(".icon").textContent)).size === 25
    && cards.every((c) => c.textContent.trim() === c.querySelector(".icon").textContent.trim()), cards.length);
  T.checkFit("who (class of 25)");

  cards[0].click(); await T.wait(900);
  await T.post("/api/progress/complete", { world: "mouse", level: 1, stars: 3 });

  document.querySelector("#parent-btn").click(); await T.wait(300); await digits("2468");
  button("👧").click(); await T.wait(800);
  const table = modal().querySelector(".class-overview table");
  T.check("the class overview lists every child and every stage", table && table.querySelectorAll("tbody tr").length === 25 && table.querySelectorAll("thead th").length === 9, table && table.querySelectorAll("thead th").length);

  // The page may not fetch blob: URLs (its Content-Security-Policy), so the test keeps the file's Blob instead.
  let blob = null;
  const realUrl = URL.createObjectURL, realClick = HTMLAnchorElement.prototype.click;
  URL.createObjectURL = (b) => { blob = b; return "blob:test"; };
  HTMLAnchorElement.prototype.click = function () {};
  modal().querySelector(".class-csv").click(); await T.wait(300);
  URL.createObjectURL = realUrl; HTMLAnchorElement.prototype.click = realClick;
  const text = blob ? await blob.text() : "";
  const lines = text.replace(/^﻿/, "").split("\r\n");
  T.check("the CSV has a header and one line per child", lines.length === 26 && lines[0].startsWith('"Kind"'), lines.length + " " + lines[0]);
  T.check("the CSV has only pictures, no names", !/Spieler|Player/.test(text));

  modal().querySelector(".add-five").click(); await T.wait(800);
  T.check("five more children makes 30, the most a class can have", (await fetch("/api/profiles").then((r) => r.json())).profiles.length === 30 && !modal().querySelector(".add-five"));
});
