// Word Woods: type short words that have a picture (cat, sun, dog).
// The server picks the words (LLM cache or built-in bank) and tells us the picture for each.

const WORD_ROUND_ICONS = ["🍄", "🐿️", "🦔", "🦉", "🌲"];

function wordWoods() {
  levelPicker("words", "🌳", WORD_ROUND_ICONS, startWordRound);
}

async function startWordRound(round) {
  const maxLen = round <= 2 ? 3 : 4; // the first two rounds use the shortest words
  const { status, body } = await api(`/api/content/words?count=5&pictured=true&max_len=${maxLen}`);
  if (status !== 200 || !body.items.length) throw new Error("no words available");
  typingRound({
    screen: "words", icon: "🌳", text: t("words.type"),
    items: body.items.map((word) => ({ text: word.toUpperCase(), speak: word, picture: body.pictures[word] })),
    onDone: () => completeLevel("words", round, wordWoods),
  });
}
