// Name Nest (stage 3, "My Name"): the child types their own name, then family words (Mama, Papa, Oma, ...), then
// their favourite word, each three times. Brief section 5: the highest-motivation words come first.
// The parent sets all of them in the parent area; they never leave this computer (brief section 6.1).

const NAME_ICONS = ["📛", "👪", "💛"];

function nameNest() {
  levelPicker("name", "🪺", NAME_ICONS, (n) => {
    const done = () => completeLevel("name", n, nameNest);
    if (n === 1) return typeWords([settings.child_name], window.TIPPY_CONFIG.mascotName, "📛", "sentences.name", done);
    if (n === 2) return typeWords(settings.family_words.split(","), t("defaultFamily"), "👪", "name.family", done);
    typeWords([settings.favorite_word], t("defaultFavorite"), "💛", "sentences.fav", done);
  });
}

// Three words to type, cycling through the list (one name is typed three times). A word that cannot be typed on
// this keyboard, or an empty list, falls back to the friendly default (a comma-separated list).
function typeWords(words, fallback, icon, promptKey, done) {
  const typable = (list) => list.map((w) => foldForKeyboard(typingText(w || ""))).filter(isTypable);
  const pool = typable(words).length ? typable(words) : typable(fallback.split(","));
  const items = [0, 1, 2].map((i) => pool[i % pool.length]).map((word) => ({ text: shout(word), speak: word }));
  typingRound({ screen: "name", icon, text: t(promptKey), items, onDone: done });
}
