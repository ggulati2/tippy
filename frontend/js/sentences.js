// Sentence Sky: rounds 1 to 3 type short sentences, round 4 the child's own
// name, round 5 a favourite word. The parent sets the name and the word in the
// parent area. The name never leaves this computer.

const SKY_ICONS = ["🌤️", "⛅", "🌈", "📛", "💛"];
const SENTENCES_PER_ROUND = 3;

function sentenceSky() {
  levelPicker("sentences", "☁️", SKY_ICONS, startSkyRound);
}

// Keep only what a child can type on the current keyboard, and drop full stops.
function typableEntries(sentences) {
  return sentences
    .map((original) => ({ original, text: typingText(original) }))
    .filter((entry) => isTypable(entry.text));
}

async function startSkyRound(round) {
  if (round === 4) return nameRound(settings.child_name, "sentences.name", window.TIPPY_CONFIG.mascotName);
  if (round === 5) return nameRound(settings.favorite_word, "sentences.fav", t("defaultFavorite"));

  const { status, body } = await api("/api/content/sentences?count=10");
  if (status !== 200) throw new Error("no sentences available");
  // Shortest first, so round 1 is easiest. Rounds 1, 2 and 3 take the short, middle and long ones.
  const entries = typableEntries(body.items).sort((a, b) => a.text.length - b.text.length);
  const start = Math.min((round - 1) * SENTENCES_PER_ROUND, Math.max(0, entries.length - SENTENCES_PER_ROUND));
  const chosen = entries.slice(start, start + SENTENCES_PER_ROUND);
  if (!chosen.length) chosen.push({ original: "I like to type.", text: "I like to type" });
  typingRound({
    screen: "sentences", icon: "☁️", text: t("sentences.type"),
    items: chosen.map((entry) => ({ text: entry.text.toUpperCase(), speak: entry.original })),
    onDone: () => completeLevel("sentences", round, sentenceSky),
  });
}

// The child types their own name (or favourite word) three times.
function nameRound(value, promptKey, fallback) {
  let text = typingText(value || "");
  if (!isTypable(text)) text = typingText(fallback); // not set yet: use a friendly default
  const round = promptKey === "sentences.name" ? 4 : 5;
  typingRound({
    screen: "sentences", icon: round === 4 ? "📛" : "💛", text: t(promptKey),
    items: [text, text, text].map((word) => ({ text: word.toUpperCase(), speak: word })),
    onDone: () => completeLevel("sentences", round, sentenceSky),
  });
}
