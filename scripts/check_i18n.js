// Checks that English and German have exactly the same text keys, and that every t("...") key
// used in the code exists. Run by scripts/check.sh. Needs Node.js (skipped if not installed).
global.window = global;
const fs = require("fs");
new Function(fs.readFileSync("frontend/js/i18n.js", "utf8"))();
const S = window.STRINGS, en = Object.keys(S.en), de = Object.keys(S.de);
const problems = [];
for (const k of en) if (!(k in S.de)) problems.push(`missing in German: ${k}`);
for (const k of de) if (!(k in S.en)) problems.push(`missing in English: ${k}`);
const code = fs.readdirSync("frontend/js").filter((f) => f !== "i18n.js")
  .map((f) => fs.readFileSync("frontend/js/" + f, "utf8")).join("\n");
const used = [...code.matchAll(/\bt\("([A-Za-z0-9._]+)"\)/g)].map((m) => m[1]);
for (const k of new Set(used)) if (!en.includes(k)) problems.push(`used in code but not defined: ${k}`);
if (problems.length) { console.error(problems.join("\n")); process.exit(1); }
console.log(`i18n ok (${en.length} keys in each language)`);
