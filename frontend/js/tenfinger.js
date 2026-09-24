// Ten-Finger Path (docs/REVAMP_BRIEF.md section 5, "Optional, 7+"): a gentle first look at typing with
// fingers resting on the home row. It stays locked until a parent opens it. The on-screen keyboard
// already colours every key by the finger that presses it, so the lessons only choose which keys.

const TENFINGER_ICONS = ["👆", "🤚", "✋", "🙌", "📝"];

// Only home-row letters (A S D F G H J K L), so every item can be typed without leaving the home row
// on QWERTY and QWERTZ alike.
const TENFINGER_DRILLS = [
  ["F", "J", "FJ", "JF", "FJF"],                  // the two keys with a bump: where the pointer fingers rest
  ["AS", "DF", "ASDF", "FDSA", "SAFD"],            // left hand
  ["JK", "KL", "JKL", "LKJ", "JLK"],               // right hand
  ["FJ DK", "SL AK", "ASDF JKL", "GH", "FG HJ"],   // both hands, and the reach to G and H
];
const TENFINGER_WORDS = {
  en: ["dad", "sad", "all", "fall", "glad"],
  de: ["das", "als", "Glas", "Hals", "Saal"],
  es: ["sala", "hada", "falda", "salsa", "gala"],
};

function tenFingerPath() {
  levelPicker("tenfinger", "🖐️", TENFINGER_ICONS, (n) => {
    const words = n === 5 ? (TENFINGER_WORDS[settings.language] || TENFINGER_WORDS.en) : TENFINGER_DRILLS[n - 1];
    typingRound({
      screen: "tenfinger", icon: TENFINGER_ICONS[n - 1], text: t("tf." + n),
      items: words.map((w) => ({ text: shout(w), speak: w })),
      onDone: () => completeLevel("tenfinger", n, tenFingerPath),
    });
  });
}
