// Sentence Sky: rounds 1 to 3 type short sentences, shortest first, then bonus levels.
// (The name and favourite-word rounds moved to Name Nest, name.js.)

const SKY_ICONS = ["🌤️", "⛅", "🌈"];
const SENTENCES_PER_ROUND = 3;

const SENTENCE_BONUS = {
  4: { kind: "long", text: "sentences.long", icon: "🦜" },
  5: { kind: "question", text: "sentences.question", icon: "❓" },
  6: { kind: "themed", text: "sentences.themed", icon: "💛" },
  // German only (content/special.json)
  7: { special: "culture_sentences", text: "de.sentences.culture", icon: "🏰" },
  8: { special: "festival_sentences", text: "de.sentences.festivals", icon: "🎃" },
  // For every language (content/special.json)
  9: { special: "country_sentences", text: "sentences.countries", icon: "🗺️" },
  10: { special: "food_sentences", text: "sentences.food", icon: "🍰" },
  11: { special: "wild_sentences", text: "sentences.wild", icon: "🐪" },
};

// Three sentences, shortest first, for one of the bonus levels. A tiny story from the online helper keeps its order.
function bonusSentences(round, bonus, sentences, source) {
  const entries = typableEntries(sentences);
  const chosen = source === "story" ? entries : entries.sort((a, b) => a.text.length - b.text.length).slice(0, SENTENCES_PER_ROUND);
  if (!chosen.length) throw new Error("no typable sentences");
  typingRound({
    screen: "sentences", icon: bonus.icon, text: t(bonus.text),
    items: chosen.map((entry) => ({ text: shout(entry.text), speak: entry.original })),
    onDone: () => completeLevel("sentences", round, sentenceSky),
  });
}

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
  // Bonus levels: longer sentences, questions, and sentences about what the child likes.
  const bonus = SENTENCE_BONUS[round];
  const { status, body } = await api(!bonus ? "/api/content/sentences?count=10"
    : bonus.special ? `/api/content/special?set=${bonus.special}&count=6` : `/api/content/sentences?count=6&kind=${bonus.kind}`);
  if (status !== 200) throw new Error("no sentences available");
  if (bonus) return bonusSentences(round, bonus, body.items, body.source);
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
