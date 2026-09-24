// Desktop Dock: a pretend computer desktop, safe to play with. The child opens files, sorts them into
// folders, gives a file a name, throws one in the trash bin and brings it back, and saves a picture.
// Everything here is a picture on the page. No real files are touched.

const DESKTOP_ICONS = ["📄", "📁", "✏️", "🗑️", "💾", "🔑", "🪧"];
const DESKTOP_LEVELS = [deskOpen, deskSort, deskRename, deskTrash, deskSave, deskLogin, deskPopup];

function desktopDock() {
  levelPicker("desktop", "🗂️", DESKTOP_ICONS, (n) => {
    DESKTOP_LEVELS[n - 1](() => completeLevel("desktop", n, desktopDock));
  });
}

const deskNeeds = (what) => { $("#screen").dataset.need = what; };

// A small window with a title bar and a red X. `body` is what is inside.
function deskWindow(icon, body, { onClose }) {
  let closed = false;                                  // a child often double-clicks the X: it must count once
  const close = el("button", { class: "close-x", "aria-label": "close" }, "✕");
  close.addEventListener("click", () => {
    if (closed) return;
    closed = true;
    sfx("tap");
    onClose(node);
  });
  const node = el("div", { class: "win opening" }, el("div", { class: "win-bar" }, el("span", { class: "win-icon" }, icon), close), el("div", { class: "win-body" }, ...body));
  return { node, close };
}

// Lets a picture be dragged with the mouse and dropped on a target. Same idea as the baskets in Mouse Meadow.
//   targetClass: class of the drop targets;  accepts(target): may it go there?
//   onAccepted(target): it was dropped in the right place;  onMissed(): it was not (the file glides home).
function makeDraggable(item, { targetClass, accepts, onAccepted, onMissed }) {
  let startX = 0, startY = 0;
  item.addEventListener("pointerdown", (e) => {
    try { item.setPointerCapture(e.pointerId); } catch (err) { /* fine without */ }
    startX = e.clientX; startY = e.clientY;
    item.classList.add("dragging");
    item.style.transition = "none";
    sfx("key");
  });
  item.addEventListener("pointermove", (e) => {
    if (!item.classList.contains("dragging")) return;
    item.style.transform = `translate(${e.clientX - startX}px, ${e.clientY - startY}px)`;
  });
  item.addEventListener("pointerup", (e) => {
    if (!item.classList.contains("dragging")) return;
    item.classList.remove("dragging");
    const target = document.elementsFromPoint(e.clientX, e.clientY).find((n) => n.classList?.contains(targetClass));
    if (target && accepts(target)) {
      item.style.transform = "";
      onAccepted(target);
      return;
    }
    item.style.transition = "transform .35s ease";     // wrong place: glide home, no buzzer
    item.style.transform = "";
    onMissed(target);
  });
}

// ---------- Level 1: double-click to open, X to close ----------
function deskOpen(done) {
  const desk = el("div", { class: "desk" });
  const file = el("button", { class: "desk-file file-open", "aria-label": "file" }, "📄");
  desk.append(file);
  const bubble = liveInstruction("📄", t("desk.open"));
  setScreen("desktop-1", bubble.node, desk);
  deskNeeds("dblclick");
  // One click only selects the file (it stays still and gets a coloured edge); a quick second click opens it.
  onDoubleClick(file, () => {
    if (desk.querySelector(".win")) return;
    file.classList.remove("selected");
    sfx("boing");
    const win = deskWindow("📄", [el("div", { class: "win-picture" }, "🐱")], {
      onClose: (node) => { node.classList.add("closing"); sfx("home"); deskNeeds(""); later(done, 500); },
    });
    desk.append(win.node);
    bubble.set("✕", t("desk.close"));
    deskNeeds("close");
  }, () => { file.classList.add("selected"); sfx("key"); });
}

// ---------- Level 2: sort into folders ----------
function deskSort(done) {
  const files = [["🖼️", "pic"], ["🎵", "music"], ["🖼️", "pic"], ["🎵", "music"]];
  let placed = 0;
  const desk = el("div", { class: "desk" });
  const folders = el("div", { class: "desk-row" }, ...[["pic", "🖼️"], ["music", "🎵"]].map(([kind, icon]) =>
    el("div", { class: "folder", "data-kind": kind }, el("span", { class: "folder-icon" }, "📁"), el("span", { class: "folder-tag" }, icon))));
  const tray = el("div", { class: "desk-row" });
  const dots = progressDots(0, files.length);
  for (const [emoji, kind] of files) {
    const item = el("div", { class: "desk-file draggable", "data-kind": kind }, emoji);
    makeDraggable(item, {
      targetClass: "folder",
      accepts: (target) => target.dataset.kind === kind,
      onAccepted: (target) => {
        item.remove();
        target.classList.add("full");
        sfx("success");
        placed++;
        dots.textContent = progressDots(placed, files.length).textContent;
        if (placed === files.length) { deskNeeds(""); later(done, 800); }
      },
      onMissed: () => {
        const right = folders.querySelector(`[data-kind="${kind}"]`);
        right.classList.add("hint");
        setTimeout(() => right.classList.remove("hint"), 1800);
        speak(t("mouse.tryBasket"));
      },
    });
    tray.append(item);
  }
  desk.append(folders, tray);
  setScreen("desktop-2", instruction("📁", t("desk.sort")), dots, desk);
  deskNeeds("sort");
}

// ---------- Level 3: give the file a name (typing) ----------
function deskRename(done) {
  const name = window.TIPPY_CONFIG.mascotName;
  typingRound({
    screen: "desktop-3", icon: "✏️", text: t("desk.rename"),
    items: [{ text: shout(name), speak: name, picture: "📄" }],
    onDone: done,
  });
}

// ---------- Level 4: the trash bin, and how to get a file back ----------
function deskTrash(done) {
  const desk = el("div", { class: "desk" });
  const file = el("div", { class: "desk-file draggable", "data-kind": "file" }, "📄");
  const bin = el("button", { class: "desk-file trash", "aria-label": "trash bin" }, "🗑️");
  const bubble = liveInstruction("🗑️", t("desk.trash"));
  desk.append(el("div", { class: "desk-row" }, file, bin));
  setScreen("desktop-4", bubble.node, desk);
  deskNeeds("trash-drag");
  let phase = "drag";

  makeDraggable(file, {
    targetClass: "trash",
    accepts: () => phase === "drag",
    onAccepted: () => {
      file.hidden = true;
      bin.textContent = "🗑️📄";
      sfx("home");
      phase = "open";
      bubble.set("♻️", t("desk.restore"));
      bin.classList.add("hint");
      deskNeeds("trash-open");
    },
    onMissed: () => { bin.classList.add("hint"); setTimeout(() => bin.classList.remove("hint"), 1800); speak(t("mouse.tryBasket")); },
  });

  bin.addEventListener("click", () => {
    if (phase !== "open") return;
    phase = "restore";
    bin.classList.remove("hint");
    sfx("tap");
    bubble.set("↩️", t("desk.restore2"));
    const back = el("button", { class: "restore-btn attention-btn", "aria-label": "put back" }, "↩️");
    const win = deskWindow("🗑️", [el("div", { class: "trash-list" }, el("span", { class: "desk-file" }, "📄"), back)], {
      onClose: (node) => node.remove(),
    });
    desk.append(win.node);
    deskNeeds("restore");
    back.addEventListener("click", () => {
      if (phase !== "restore") return;
      phase = "done";
      win.node.remove();
      file.hidden = false;
      bin.textContent = "🗑️";
      sfx("success");
      speak(t("desk.trash.fact"));
      deskNeeds("");
      later(done, 2400);
    });
  });
}

// ---------- Level 5: save your work ----------
function deskSave(done) {
  const desk = el("div", { class: "desk" });
  const bubble = liveInstruction("💾", t("desk.saveit"));
  const picture = el("div", { class: "win-picture" }, "🖼️");
  const save = el("button", { class: "tool-btn save-btn attention-btn", "aria-label": "save" }, "💾");
  const edit = el("button", { class: "tool-btn edit-btn", "aria-label": "draw", disabled: "" }, "✏️");
  const status = el("span", { class: "win-status" }, "•");
  let phase = "save";                                  // save -> edit -> close -> ask
  const win = deskWindow("🖼️", [el("div", { class: "win-tools" }, save, edit, status), picture], {
    onClose: () => {
      const ask = el("div", { class: "dialog" }, el("div", { class: "dialog-text" }, t("desk.ask")),
        el("div", { class: "choices" },
          el("button", { class: "choice dlg-save", "aria-label": "save" }, "💾"),
          el("button", { class: "choice dlg-drop", "aria-label": "do not save" }, "🗑️")));
      phase = "ask";
      speak(t("desk.ask"));
      deskNeeds("dialog");
      ask.querySelector(".dlg-drop").addEventListener("click", (e) => {      // wrong answer: only a hint, the dialog stays
        replayAnimation(e.currentTarget, "wobble"); sfx("key");
        replayAnimation(ask.querySelector(".dlg-save"), "attention");
        speak(t("basics.tryAgain"));
      });
      ask.querySelector(".dlg-save").addEventListener("click", () => {
        if (phase !== "ask") return;
        phase = "done";
        sfx("success");
        ask.remove();
        win.node.classList.add("closing");
        speak(t("desk.saved"));
        deskNeeds("");
        later(done, 2200);
      });
      desk.append(ask);
    },
  });
  // The X is only allowed once there is something unsaved (the ask-to-save dialog is the lesson).
  win.close.disabled = true;
  desk.append(win.node);
  setScreen("desktop-5", bubble.node, desk);
  deskNeeds("save");

  save.addEventListener("click", () => {
    if (phase === "save") {
      phase = "edit";
      status.textContent = "✔";
      sfx("success");
      save.classList.remove("attention-btn");
      edit.disabled = false; edit.classList.add("attention-btn");
      bubble.set("✏️", t("desk.edit"));
      deskNeeds("edit");
    } else if (phase === "close") {                    // saving again is fine too
      status.textContent = "✔"; sfx("success");
    }
  });
  edit.addEventListener("click", () => {
    if (phase !== "edit") return;
    phase = "close";
    picture.textContent = "🖼️⭐";
    status.textContent = "•";
    sfx("sparkle");
    edit.classList.remove("attention-btn");
    win.close.disabled = false; win.close.classList.add("attention-btn");
    bubble.set("✕", t("desk.closeit"));
    deskNeeds("close");
  });
}

// ---------- Level 6: log in with a picture password ----------
// Brief section 6.2: "choose three pictures in order," which teaches that a password is a secret
// the child picks, not something anyone can guess by trying every button.
const LOGIN_PICS = ["🐱", "🐶", "🌞", "🚗", "🎈", "🐟", "⭐", "🍎"];

function deskLogin(done) {
  const shuffled = [...LOGIN_PICS].sort(() => Math.random() - 0.5);
  const secret = shuffled.slice(0, 3);
  const grid = [...secret, ...shuffled.slice(3, 6)].sort(() => Math.random() - 0.5);
  let picked = 0;
  const hint = el("div", { class: "choices login-hint" }, ...secret.map((p) => el("div", { class: "choice small" }, p)));
  const board = el("div", { class: "choices" });
  const tiles = grid.map((pic) => {
    const tile = el("button", { class: "choice", onclick: () => {
      if (tile.disabled) return;
      if (secret[picked] === pic) {
        sfx("tap"); tile.classList.add("chosen"); tile.disabled = true; picked++;
        if (picked === secret.length) { sfx("success"); deskNeeds(""); later(done, 900); }
        else deskNeeds("login:" + secret.slice(picked).join(","));
      } else {
        sfx("key"); tile.classList.add("wobble"); setTimeout(() => tile.classList.remove("wobble"), 500);
      }
    } }, pic);
    return tile;
  });
  board.append(...tiles);
  setScreen("desktop-6", instruction("🔑", t("desk.login")), hint, board);
  deskNeeds("login:" + secret.join(","));
}

// ---------- Level 7: recognise and close a pop-up ----------
function deskPopup(done) {
  const desk = el("div", { class: "desk" });
  const bubble = instruction("🖥️", t("desk.popup.close"));
  const claim = el("button", { class: "attention-btn popup-claim" }, "🎉 " + t("desk.popup.claim"));
  claim.addEventListener("click", () => { sfx("key"); replayAnimation(claim, "wobble"); });
  const win = deskWindow("🪧", [el("div", { class: "win-picture" }, "🎉"), claim], {
    onClose: (node) => { node.classList.add("closing"); sfx("home"); deskNeeds(""); later(done, 500); },
  });
  desk.append(win.node);
  setScreen("desktop-7", bubble, desk);
  deskNeeds("close");
}
