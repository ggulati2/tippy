// Internet Island: what using the internet feels like, in a pretend browser that loads nothing real.
// The child clicks links, uses the Back button, searches by typing, learns what to do with pop-ups and
// strangers, and keeps a favourite page. Every "web page" here is a picture drawn by the app itself.

const INTERNET_ICONS = ["🔗", "⬅️", "🔍", "🎁", "⭐"];

function internetIsland() {
  levelPicker("internet", "🌐", INTERNET_ICONS, (n) => {
    [netLinks, netBack, netSearch, netPopups, netFavourites][n - 1](() => completeLevel("internet", n, internetIsland));
  });
}

const netNeeds = (what) => { $("#screen").dataset.need = what; };

// The pages of the pretend web: a name (for the fake address) and a big picture.
const NET_PAGES = { dog: "🐶", rocket: "🚀", apple: "🍎" };

// A browser window: Back, Home, the address, a star for favourites and a page area.
function netBrowser() {
  const back = el("button", { class: "br-btn br-back", "aria-label": "back" }, "⬅️");
  const home = el("button", { class: "br-btn br-home", "aria-label": "home" }, "🏠");
  const address = el("div", { class: "br-address" }, "🔒 kids.tippy");
  const star = el("button", { class: "br-btn br-star", "aria-label": "favourite" }, "☆");
  const favs = el("button", { class: "br-btn br-favs", "aria-label": "favourites", hidden: "" }, "⭐📚");
  const page = el("div", { class: "br-page" });
  return { node: el("div", { class: "browser" }, el("div", { class: "br-bar" }, back, home, address, star, favs), page), back, home, star, favs, page, address };
}

// The start page: a big card for each link. `onOpen(name)` is called when the right link is clicked.
function netHomePage(browser, { wanted, onOpen }) {
  browser.address.textContent = "🔒 kids.tippy";
  browser.page.replaceChildren(el("div", { class: "link-row" }, ...Object.entries(NET_PAGES).map(([name, emoji]) => {
    const card = el("button", { class: "link-card", "data-page": name, "aria-label": name }, emoji);
    card.addEventListener("click", () => {
      if (wanted && name !== wanted()) {              // another link: it wobbles and the right one pulses (nothing bad happens)
        replayAnimation(card, "wobble"); sfx("key");
        const right = browser.page.querySelector(`[data-page="${wanted()}"]`);
        if (right) replayAnimation(right, "attention");
        speak(t("basics.tryAgain"));
        return;
      }
      sfx("tap");
      onOpen(name);
    });
    return card;
  })));
}

function netArticlePage(browser, name) {
  browser.address.textContent = `🔒 kids.tippy/${name}`;
  browser.page.replaceChildren(el("div", { class: "article", "data-page": name }, NET_PAGES[name]));
}

// ---------- Level 1: click a link ----------
function netLinks(done) {
  const browser = netBrowser();
  browser.back.disabled = true;
  const bubble = liveInstruction("🚀", t("net.link"));
  setScreen("internet-1", bubble.node, browser.node);
  netNeeds("link:rocket");
  netHomePage(browser, {
    wanted: () => "rocket",
    onOpen: (name) => { netArticlePage(browser, name); sfx("success"); netNeeds(""); later(done, 1200); },
  });
}

// ---------- Level 2: the Back button ----------
function netBack(done) {
  const browser = netBrowser();
  let phase = "link";
  const bubble = liveInstruction("🐶", t("net.dog"));
  setScreen("internet-2", bubble.node, browser.node);
  browser.back.disabled = true;
  netNeeds("link:dog");
  const showHome = () => netHomePage(browser, {
    wanted: () => "dog",
    onOpen: (name) => {
      netArticlePage(browser, name);
      phase = "back";
      browser.back.disabled = false;
      browser.back.classList.add("attention-btn");
      bubble.set("⬅️", t("net.back"));
      netNeeds("back");
    },
  });
  showHome();
  browser.back.addEventListener("click", () => {
    if (phase !== "back") return;
    phase = "done";
    sfx("home");
    browser.back.classList.remove("attention-btn");
    showHome();
    netNeeds("");
    later(done, 900);
  });
}

// ---------- Level 3: search by typing ----------
function netSearch(done) {
  const words = { en: "dog", de: "hund", es: "perro" };
  const word = words[settings.language] || words.en;
  typingRound({
    screen: "internet-3", icon: "🔍", text: t("net.search"),
    items: [{ text: shout(word), speak: word, picture: "🔍" }],
    onDone: () => chooseSteps("internet-choose", [
      { icon: "🐶", prompt: t("net.result"), scene: "🔍", options: [{ emoji: "🐶" }, { emoji: "🐱" }, { emoji: "🐟" }], answer: 0 },
    ], done),
  });
}

// ---------- Level 4: pop-ups, downloads and strangers ----------
function netPopups(done) {
  const help = [{ emoji: "🙋" }];
  chooseSteps("internet-4", [
    { icon: "🎁", prompt: t("net.pop1"), scene: "🎉🎁🎉", options: [...help, { emoji: "🎁" }, { emoji: "👆" }], answer: 0, fact: t("net.pop.fact") },
    { icon: "⬇️", prompt: t("net.pop2"), scene: "⬇️🎮", options: [...help, { emoji: "⬇️" }, { emoji: "✅" }], answer: 0, fact: t("net.pop.fact") },
    { icon: "🕵️", prompt: t("net.pop3"), scene: "🕵️❓", options: [...help, { emoji: "⌨️" }, { emoji: "🏠" }], answer: 0, fact: t("net.pop.fact") },
  ], done);
}

// ---------- Level 5: keep a favourite page ----------
function netFavourites(done) {
  const browser = netBrowser();
  let phase = "link";                                  // link -> star -> home -> favs -> item
  const bubble = liveInstruction("🐶", t("net.dog"));
  setScreen("internet-5", bubble.node, browser.node);
  browser.back.disabled = true;
  let kept = false;

  const showHome = () => netHomePage(browser, {
    wanted: () => "dog",
    onOpen: (name) => {
      netArticlePage(browser, name);
      if (phase === "link") {
        phase = "star";
        browser.star.classList.add("attention-btn");
        bubble.set("⭐", t("net.fav"));
        netNeeds("star");
      }
    },
  });
  showHome();
  netNeeds("link:dog");

  browser.star.addEventListener("click", () => {
    if (phase !== "star") return;
    phase = "home";
    kept = true;
    browser.star.textContent = "★";
    browser.star.classList.remove("attention-btn");
    sfx("sparkle");
    browser.home.classList.add("attention-btn");
    bubble.set("🏠", t("net.fav2"));
    netNeeds("home");
  });
  browser.home.addEventListener("click", () => {
    sfx("tap");
    if (phase !== "home") return showHome();
    phase = "favs";
    browser.home.classList.remove("attention-btn");
    showHome();
    browser.star.textContent = "☆";
    browser.favs.hidden = false;
    browser.favs.classList.add("attention-btn");
    netNeeds("favs");
  });
  browser.favs.addEventListener("click", () => {
    if (phase !== "favs" || !kept) return;
    phase = "item";
    sfx("tap");
    browser.favs.classList.remove("attention-btn");
    const item = el("button", { class: "link-card fav-item attention-btn", "aria-label": "favourite page" }, NET_PAGES.dog);
    browser.address.textContent = "🔒 kids.tippy/⭐";
    browser.page.replaceChildren(el("div", { class: "link-row" }, item));
    bubble.set("🐶", t("net.fav3"));
    netNeeds("favitem");
    item.addEventListener("click", () => {
      if (phase !== "item") return;
      phase = "done";
      netArticlePage(browser, "dog");
      sfx("success");
      netNeeds("");
      later(done, 1200);
    });
  });
}
