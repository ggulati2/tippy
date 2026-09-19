// Sentence Sky: rounds 1 to 3 type short sentences, round 4 the child's own
// name, round 5 a favourite word. The parent sets the name and the word in the
// parent area. The name never leaves this computer.

const SKY_ICONS = ["🌤️", "⛅", "🌈", "📛", "💛"];
const SENTENCES_PER_ROUND = 3;

const SENTENCE_BONUS = {
  6: { kind: "long", text: "sentences.long", icon: "🦜" },
  7: { kind: "question", text: "sentences.question", icon: "❓" },
  8: { kind: "themed", text: "sentences.themed", icon: "💛" },
  // German only (content/special.json)
  9: { special: "culture_sentences", text: "de.sentences.culture", icon: "🏰" },
  10: { special: "festival_sentences", text: "de.sentences.festivals", icon: "🎃" },
};

// Three sentences, shortest first, for one of the bonus levels.
function bonusSentences(round, bonus, sentences) {
  const chosen = typableEntries(sentences).sort((a, b) => a.text.length - b.text.length).slice(0, SENTENCES_PER_ROUND);
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
  if (round === 4) return nameRound(settings.child_name, "sentences.name", window.TIPPY_CONFIG.mascotName);
  if (round === 5) return nameRound(settings.favorite_word, "sentences.fav", t("defaultFavorite"));

  // Bonus levels: longer sentences, questions, and sentences about what the child likes.
  const bonus = SENTENCE_BONUS[round];
  const { status, body } = await api(!bonus ? "/api/content/sentences?count=10"
    : bonus.special ? `/api/content/special?set=${bonus.special}&count=6` : `/api/content/sentences?count=6&kind=${bonus.kind}`);
  if (status !== 200) throw new Error("no sentences available");
  if (bonus) return bonusSentences(round, bonus, body.items);
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
  let text = foldForKeyboard(typingText(value || ""));
  if (!isTypable(text)) text = typingText(fallback); // not set yet: use a friendly default
  const round = promptKey === "sentences.name" ? 4 : 5;
  typingRound({
    screen: "sentences", icon: round === 4 ? "📛" : "💛", text: t(promptKey),
    items: [text, text, text].map((word) => ({ text: word.toUpperCase(), speak: word })),
    onDone: () => completeLevel("sentences", round, sentenceSky),
  });
}
