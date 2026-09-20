// Word Woods: type short words that have a picture (cat, sun, dog).
// The server picks the words (LLM cache or built-in bank) and tells us the picture for each.

const WORD_ROUND_ICONS = ["🍄", "🐿️", "🦔", "🦉", "🌲"];

function wordWoods() {
  levelPicker("words", "🌳", WORD_ROUND_ICONS, startWordRound);
}

// Bonus levels: longer words, then one themed set each (the words come from the built-in bank).
const WORD_BONUS = {
  6: { query: "min_len=5&max_len=8", text: "words.long", icon: "🐘" },
  7: { query: "theme=animals&max_len=8", text: "words.animals", icon: "🐾" },
  8: { query: "theme=space&max_len=8", text: "words.space", icon: "🚀" },
  9: { query: "theme=dinosaurs&max_len=8", text: "words.dinos", icon: "🦖" },
  10: { query: "theme=vehicles&max_len=8", text: "words.vehicles", icon: "🚗" },
  // German only: words about Germany and the year's festivals (content/special.json)
  11: { special: "culture_words", text: "de.culture", icon: "🥨" },
  12: { special: "festival_words", text: "de.festivals", icon: "🎄" },
  // For every language (content/special.json)
  13: { special: "country_words", text: "words.countries", icon: "🌍" },
  14: { special: "food_words", text: "words.food", icon: "🍕" },
  15: { special: "wild_words", text: "words.wild", icon: "🦓" },
};

async function startWordRound(round) {
  const bonus = WORD_BONUS[round];
  const maxLen = round <= 2 ? 3 : 4; // the first two rounds use the shortest words
  const url = bonus && bonus.special ? `/api/content/special?set=${bonus.special}&count=5`
    : `/api/content/words?count=5&pictured=true&${bonus ? bonus.query : "max_len=" + maxLen}`;
  const { status, body } = await api(url);
  if (status !== 200 || !body.items.length) throw new Error("no words available");
  typingRound({
    screen: "words", icon: bonus ? bonus.icon : "🌳", text: t(bonus ? bonus.text : "words.type"),
    items: body.items.map((word) => ({ text: shout(word), speak: word, picture: body.pictures[word] })),
    onDone: () => completeLevel("words", round, wordWoods),
  });
}
