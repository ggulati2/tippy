// Checks the screen texts of every language:
//  - every language listed in backend/languages.py has a block of texts,
//  - every language has exactly the same keys as English,
//  - every t("...") key used in the code is defined.
// Run by scripts/check.sh. Needs Node.js (skipped if not installed).
global.window = global;
const fs = require("fs");
const load = (file) => new Function(fs.readFileSync(file, "utf8"))();
load("frontend/js/i18n.js");
for (const file of fs.readdirSync("frontend/js").filter((f) => /^i18n-.+\.js$/.test(f))) load("frontend/js/" + file);

const S = window.STRINGS, problems = [];
const englishKeys = Object.keys(S.en);

const listed = [...fs.readFileSync("backend/languages.py", "utf8").matchAll(/^\s+"([a-z]{2})": \{"native"/gm)].map((m) => m[1]);
for (const code of listed) if (!S[code]) problems.push(`language "${code}" is listed in backend/languages.py but has no texts`);
for (const code of Object.keys(S)) if (!listed.includes(code)) problems.push(`texts exist for "${code}" but it is not listed in backend/languages.py`);

// A key starting with a language code and a dot ("de.b11.fire") belongs to content that exists in that
// language only. It is required in that language and allowed nowhere else.
const owner = (key) => { const m = key.match(/^([a-z]{2})\./); return m && listed.includes(m[1]) ? m[1] : null; };
for (const code of Object.keys(S)) {
  for (const k of Object.keys(S[code])) if (owner(k) && owner(k) !== code) problems.push(`"${k}" is a ${owner(k)} key but is defined in ${code}`);
}
const shared = englishKeys.filter((k) => !owner(k));
for (const code of Object.keys(S).filter((c) => c !== "en")) {
  for (const k of shared) if (!(k in S[code])) problems.push(`missing in ${code}: ${k}`);
  for (const k of Object.keys(S[code])) if (!(k in S.en) && owner(k) !== code) problems.push(`in ${code} but not in English: ${k}`);
  for (const k of Object.keys(S[code])) if (!S[code][k] || typeof S[code][k] !== "string") problems.push(`empty text in ${code}: ${k}`);
}

const code = fs.readdirSync("frontend/js").filter((f) => !f.startsWith("i18n")).map((f) => fs.readFileSync("frontend/js/" + f, "utf8")).join("\n");
const used = [...code.matchAll(/\bt\("([A-Za-z0-9._]+)"\)/g)].map((m) => m[1]);
const everything = new Set(Object.values(S).flatMap((strings) => Object.keys(strings)));
for (const k of new Set(used)) if (!everything.has(k)) problems.push(`used in code but not defined: ${k}`);
for (const k of new Set(used)) if (owner(k) && !(k in S[owner(k)])) problems.push(`${k} is used but missing in ${owner(k)}`);

if (problems.length) { console.error(problems.join("\n")); process.exit(1); }
console.log(`i18n ok (${englishKeys.length} keys in each of ${Object.keys(S).length} languages: ${Object.keys(S).join(", ")})`);
