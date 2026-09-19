// Ask Tippy (the parent switches it on; it is off by default).
//
// The child taps a PICTURE ("What is the internet?"), Tippy answers in one to
// three short sentences and reads them aloud. There is deliberately no typing
// box: a fixed list of topics means the child can never send personal
// information or unsuitable questions to the online helper.

const ASK_TOPICS = [
  ["computer", "💻"], ["internet", "🌍"], ["wifi", "📶"], ["mouse", "🖱️"], ["keyboard", "⌨️"],
  ["screen", "🖥️"], ["password", "🔑"], ["app", "📱"], ["email", "✉️"], ["cloud", "☁️"],
];

function askTippy() {
  const bubble = liveInstruction("💬", t("ask.title"));
  const answer = el("div", { class: "bubble answer" }, " "); // text is set with textContent only
  const grid = el("div", { class: "ask-grid" }, ...ASK_TOPICS.map(([id, icon]) =>
    el("button", { class: "choice small", onclick: () => askTopic(id, answer) },
      el("span", { class: "choice-icon" }, icon), el("span", { class: "choice-label" }, t("ask." + id)))));
  setScreen("ask", bubble.node, grid, answer);
}

async function askTopic(topic, answerBox) {
  sfx("tap");
  answerBox.textContent = "…";
  let text = t("ask.redirect");
  try {
    const { status, body } = await api("/api/ask?topic=" + encodeURIComponent(topic));
    if (status === 200 && body.text) text = body.text;
  } catch (e) { /* offline server: the gentle fallback line is shown */ }
  answerBox.textContent = text; // escaped: never HTML
  speak(text);
}
