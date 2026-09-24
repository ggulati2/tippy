// Printable extras for the parent area (docs/REVAMP_BRIEF.md section 6.4): a certificate for every finished
// stage and a paper keyboard to colour in. They are drawn into #print-root, which is the only thing the
// print stylesheet shows, and the browser's own print dialog does the rest (print, or save as PDF).

function printCard(worlds) {
  const finished = STAGES.filter((stage) => stage.worlds.every((w) => worlds[w] && worlds[w].total && worlds[w].done >= worlds[w].total));
  const certificates = finished.length
    ? finished.map((stage) => el("button", { class: "big-btn blue small-btn print-cert", onclick: () => printCertificate(stage.key) }, "🏅 " + t(stage.key)))
    : [el("p", { class: "muted" }, t("printNone"))];
  return el("div", { class: "card print-card" }, el("h3", {}, "🖨️ " + t("printTitle")),
    el("p", {}, t("printCert")), el("div", { class: "seg wrap" }, ...certificates),
    el("div", { class: "row" }, el("button", { class: "big-btn blue small-btn print-sheet", onclick: printKeyboardSheet }, "⌨️ " + t("printSheet"))));
}

function printPage(...nodes) {
  let root = $("#print-root");
  if (!root) { root = el("div", { id: "print-root" }); document.body.append(root); }
  root.replaceChildren(...nodes);
  window.addEventListener("afterprint", () => root.replaceChildren(), { once: true });
  window.print();
}

function printCertificate(stageKey) {
  const name = settings.child_name || t("child.unnamed");
  printPage(el("div", { class: "certificate" }, mascotSVG(),
    el("h1", {}, t("certTitle")),
    el("p", { class: "cert-name" }, name),
    el("p", {}, t("certText").replace("{stage}", t(stageKey).replace(/^\d+\.\s*/, ""))),
    el("p", { class: "cert-date" }, "⭐ " + new Date().toLocaleDateString(settings.language) + " ⭐")));
}

// Every key of the child's own keyboard shape as an empty outline with its letter, to colour by finger.
function printKeyboardSheet() {
  const rows = KEY_ROWS[settings.keyboard_layout] || KEY_ROWS.qwerty;
  printPage(el("div", { class: "key-sheet" },
    el("h1", {}, t("sheetTitle")), el("p", {}, t("sheetText")),
    ...rows.map((row) => el("div", { class: "sheet-row" },
      ...row.map((key) => el("div", { class: "sheet-key" + (key.length > 1 ? " wide" : "") }, KEY_LABELS[key] || key))))));
}
