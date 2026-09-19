"""Practice content and mascot lines, served to the child without ever waiting.

Order of preference for every request:
  1. fresh items from the cache (filled earlier in the background by the LLM),
  2. items that were already used before (better than nothing),
  3. the built-in bank.
After serving, if the cache is running low, a background thread asks the LLM
for a new batch, validates it, and stores it for next time.
The child's request itself never touches the network.
"""
import json
import logging
import random
import threading
import time
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from backend import bank, db, difficulty, validators
from backend.llm.client import LLMClient
from backend.llm.schemas import SCHEMAS

log = logging.getLogger("tippy.content")

LOW_WATER = {"words": 10, "sentences": 6, "mascot": 4, "ask": 2}   # refill when fewer unused items remain
BATCH = {"words": 20, "sentences": 10, "mascot": 8, "ask": 4}      # how many to ask for at once
MIN_GOOD = {"words": 3, "sentences": 3, "mascot": 3, "ask": 1}   # a batch with fewer valid items is thrown away
COOLDOWN_SECONDS = 600  # after a failed refill, wait before asking again (free accounts have a small daily limit)
MIN_PRACTICE_LETTERS = 16  # Word Woods and Sentence Sky draw from at least this many letters (A to N in our order),
                           # or there would hardly be any real words; the on-screen keyboard guides each new key


class ContentService:
    def __init__(self, source, llm: LLMClient, background: bool = True):
        # `source` is a database Path, or an object with a `db_path` attribute (the Family), so that
        # the service always talks to the database of whoever is playing right now.
        self._source = source
        self.llm = llm
        self.background = background  # tests set False so refills run immediately
        self._inflight: set[str] = set()
        self._cooldown: dict[str, float] = {}
        self._lock = threading.Lock()

    @property
    def db_path(self) -> Path:
        return self._source.db_path if hasattr(self._source, "db_path") else self._source

    # ---------- Child profile ----------

    def language(self) -> str:
        return db.get_settings(self.db_path).get("language", "en")

    def interests(self) -> list[str]:
        """Themes from the profile, filtered to our fixed list (free text is never used in prompts)."""
        with db.connect(self.db_path) as conn:
            row = conn.execute("SELECT interests FROM child_profile WHERE id = 1").fetchone()
        chosen = [x for x in (row["interests"] if row else "").split(",") if x in bank.THEMES]
        return chosen or list(bank.THEMES)

    # ---------- Cache ----------

    def _take(self, cache_type: str, level: int, count: int) -> list[str]:
        """Take up to `count` items: unused first, then re-use old ones. Marks them used."""
        items: list[str] = []
        with db.connect(self.db_path) as conn:
            fresh = conn.execute(
                "SELECT id, json FROM content_cache WHERE type = ? AND level = ? AND used = 0 ORDER BY id LIMIT ?",
                (cache_type, level, count),
            ).fetchall()
            for row in fresh:
                items.append(json.loads(row["json"])["text"])
                conn.execute("UPDATE content_cache SET used = 1 WHERE id = ?", (row["id"],))
            if len(items) < count:
                old = conn.execute(
                    "SELECT json FROM content_cache WHERE type = ? AND level = ? AND used = 1", (cache_type, level)
                ).fetchall()
                pool = [json.loads(r["json"])["text"] for r in old]
                random.shuffle(pool)
                items += [x for x in pool if x not in items][: count - len(items)]
        return items

    def _unused(self, cache_type: str, level: int) -> int:
        with db.connect(self.db_path) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM content_cache WHERE type = ? AND level = ? AND used = 0", (cache_type, level)
            ).fetchone()[0]

    def _store(self, cache_type: str, level: int, items: list[str], db_path: Path | None = None) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with db.connect(db_path or self.db_path) as conn:
            known = {json.loads(r["json"])["text"] for r in
                     conn.execute("SELECT json FROM content_cache WHERE type = ? AND level = ?", (cache_type, level))}
            for text in items:
                if text not in known:
                    conn.execute("INSERT INTO content_cache (type, level, json, created_at) VALUES (?, ?, ?, ?)",
                                 (cache_type, level, json.dumps({"text": text}), now))

    # ---------- Background refill ----------

    def _validate(self, kind: str, text: str | None, params: dict) -> list[str]:
        """Turn the LLM's raw answer into safe items, or [] if it is not good enough."""
        if not text:
            return []
        schema, field = SCHEMAS[kind]
        try:
            reply = schema.model_validate_json(text.strip().removeprefix("```json").removesuffix("```").strip())
        except ValidationError:
            log.warning("LLM %s reply rejected: not the expected JSON", kind)
            return []
        items = getattr(reply, field)
        allowed = set(params.get("letters", ""))
        lang = params.get("lang")
        if kind == "words":
            good = validators.clean_words(items, allowed, lang)
        elif kind == "sentences":
            good = validators.clean_sentences(items, allowed, lang)
        elif kind == "ask":
            good = validators.clean_answers(items, lang)
        else:
            good = validators.clean_mascot_lines(items, lang)
        if len(good) < MIN_GOOD[kind]:
            log.warning("LLM %s reply rejected: only %d of %d items were safe", kind, len(good), len(items))
            return []
        return good

    def _refill(self, kind: str, cache_type: str, level: int, params: dict, db_path: Path) -> None:
        # db_path is the child the request was for: if another child starts playing while the
        # answer is on its way, it still lands in the right child's cache.
        key = f"{db_path.name}:{cache_type}:{level}"
        try:
            text = self.llm.generate({"kind": kind, "count": BATCH[kind], **params})
            good = self._validate(kind, text, params)
            if good:
                self._store(cache_type, level, good, db_path)
                self._cooldown.pop(key, None)
            else:
                self._cooldown[key] = time.monotonic() + COOLDOWN_SECONDS
        except Exception:
            log.exception("Background refill failed")  # never reaches the child
            self._cooldown[key] = time.monotonic() + COOLDOWN_SECONDS
        finally:
            with self._lock:
                self._inflight.discard(key)

    def _maybe_refill(self, kind: str, cache_type: str, level: int, params: dict) -> None:
        if not self.llm.enabled or self._unused(cache_type, level) >= LOW_WATER[kind]:
            return
        db_path = self.db_path
        key = f"{db_path.name}:{cache_type}:{level}"
        if time.monotonic() < self._cooldown.get(key, 0):
            return
        with self._lock:
            if key in self._inflight:
                return
            self._inflight.add(key)
        if self.background:
            threading.Thread(target=self._refill, args=(kind, cache_type, level, params, db_path), daemon=True).start()
        else:
            self._refill(kind, cache_type, level, params, db_path)

    # ---------- What the app asks for ----------

    def _practice(self, kind: str, count: int, min_letters: int = 0) -> dict:
        lang = self.language()
        unlocked = max(difficulty.get_letters(self.db_path)["unlocked"], min_letters)
        letters = difficulty.letters_for(unlocked)
        cache_type = f"{kind}:{lang}"
        items = self._take(cache_type, unlocked, count)
        from_cache = len(items)
        if from_cache < count:  # cache could not fill the request: top up from the built-in bank
            pool = bank.WORDS if kind == "words" else bank.SENTENCES
            items += bank.pick(pool, lang, set(letters), self.interests(), count - from_cache, exclude=items)
        source = "cache" if from_cache == len(items) else "fallback" if from_cache == 0 else "mixed"
        self._maybe_refill(kind, cache_type, unlocked, {"lang": lang, "letters": letters, "themes": self.interests()})
        return {"items": items, "letters": letters, "source": source}

    def words(self, count: int = 8) -> dict:
        return self._practice("words", count, min_letters=MIN_PRACTICE_LETTERS)

    def pictured_words(self, count: int = 5, max_len: int = 4, min_len: int = 0, theme: str | None = None) -> dict:
        """Words for Word Woods: only words we have a picture for, `min_len` to `max_len` letters.
        Longer words (min_len) and themed sets (theme) come from the built-in bank."""
        lang = self.language()
        pictures = bank.PICTURES.get(lang, bank.PICTURES["en"])
        if min_len or theme:
            usable = {w for w in pictures if min_len <= len(w) <= max_len}
            everything = set(difficulty.LETTER_ORDER)
            chosen = bank.pick(bank.WORDS, lang, everything, [theme] if theme else self.interests(), count,
                               only=usable, themes={theme} if theme else None)
            if len(chosen) < count:
                chosen += bank.pick(bank.WORDS, lang, everything, self.interests(), count - len(chosen), exclude=chosen, only=usable)
            return {"items": chosen, "pictures": {w: pictures[w] for w in chosen}, "source": "fallback"}
        result = self._practice("words", count * 3, min_letters=MIN_PRACTICE_LETTERS)  # ask wide, then keep the drawable ones
        chosen = [w for w in result["items"] if w in pictures and len(w) <= max_len][:count]
        if len(chosen) < count:  # top up from the built-in bank
            usable = {w for w in pictures if len(w) <= max_len}
            chosen += bank.pick(bank.WORDS, lang, set(result["letters"]), self.interests(), count - len(chosen),
                                exclude=chosen, only=usable)
        return {"items": chosen, "pictures": {w: pictures[w] for w in chosen}, "source": result["source"]}

    def sentences(self, count: int = 4, kind: str = "normal") -> dict:
        """Sentences for Sentence Sky. kind: normal, long (5 or more words), question, or themed (the child's interests)."""
        if kind == "normal":
            return self._practice("sentences", count, min_letters=MIN_PRACTICE_LETTERS)
        everything = set(difficulty.LETTER_ORDER)
        themes = {bank.QUESTIONS} if kind == "question" else set(self.interests()) if kind == "themed" else None
        items = bank.pick(bank.SENTENCES, self.language(), everything, self.interests(), count, themes=themes,
                          min_words=5 if kind == "long" else 0)
        return {"items": items, "letters": list(difficulty.LETTER_ORDER), "source": "fallback"}

    def special(self, name: str, count: int) -> dict | None:
        """A set that exists for one language only (Germany-specific words and sentences). None if this
        language has no such set."""
        spec = bank.SPECIAL.get(self.language(), {}).get(name)
        if not spec:
            return None
        if spec["type"] == "words":
            words = random.sample(list(spec["items"]), min(count, len(spec["items"])))
            return {"items": words, "pictures": {w: spec["items"][w] for w in words}, "source": "special"}
        return {"items": random.sample(spec["items"], min(count, len(spec["items"]))), "source": "special"}

    def mascot_line(self, event: str) -> str:
        if event not in bank.MASCOT_LINES["en"]:
            event = "welcome"
        lang = self.language()
        cache_type = f"mascot:{lang}:{event}"
        taken = self._take(cache_type, 0, 1)
        self._maybe_refill("mascot", cache_type, 0, {"lang": lang, "event": event})
        return taken[0] if taken else bank.local_mascot_line(lang, event)

    def ask_answer(self, topic: str) -> dict:
        """Answer for an "Ask Tippy" picture topic. The child never types a question:
        the topic comes from a fixed list, so no personal text can ever reach the LLM."""
        lang = self.language()
        if topic not in bank.ASK["questions"]:
            return {"text": bank.ASK_REDIRECT.get(lang, bank.ASK_REDIRECT["en"]), "source": "redirect"}
        cache_type = f"ask:{lang}:{topic}"
        taken = self._take(cache_type, 0, 1)
        self._maybe_refill("ask", cache_type, 0, {"lang": lang, "topic": topic})
        if taken:
            return {"text": taken[0], "source": "cache"}
        return {"text": bank.ASK["answers"].get(lang, bank.ASK["answers"]["en"])[topic], "source": "builtin"}
