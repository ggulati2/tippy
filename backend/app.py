"""The Tippy web server (FastAPI).

It only listens on 127.0.0.1, so nobody else on the network can reach it.
It serves the frontend files and a few small JSON endpoints under /api.
"""
import dataclasses
import json
import logging
import os
import threading

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from datetime import date

from backend import bank, dashboard, db, difficulty, languages, licence, progress, restore, summary
from backend.config import FRONTEND_DIR, LOG_DIR, PORT, load_settings
from backend.content import ContentService
from backend.llm.client import LLMClient
from backend import profiles as profiles_module
from backend.profiles import AVATARS, Family, ProfileError
from backend.security import PinGuard

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_DIR / "tippy.log", encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("tippy")


# Names may contain any letters (Zoë, José, Åsa, Jürgen), spaces, hyphens and apostrophes. They are only
# ever shown with textContent and never sent to the LLM. The typing games fold accents to plain
# keys on the child's side (see foldForKeyboard in typing.js).
NAME_PATTERN = r"^[\p{L} '\-]{0,20}$"
WORD_PATTERN = r"^[\p{L}]{0,15}$"


# The biggest request Tippy accepts: a backup file is limited to 5 MB (restore.MAX_BACKUP_BYTES) plus a little room.
MAX_REQUEST_BYTES = restore.MAX_BACKUP_BYTES + 256 * 1024

SECURITY_HEADERS = {
    # Only our own files, and only talking to ourselves. No inline scripts, no frames, no forms sent elsewhere.
    "Content-Security-Policy": ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
                                "connect-src 'self'; media-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; "
                                "frame-ancestors 'none'"),
    "X-Frame-Options": "DENY",                                  # nobody may show Tippy inside another page
    "X-Content-Type-Options": "nosniff",                        # a file is what its type says it is
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",   # Tippy never needs these
}


def create_app() -> FastAPI:
    settings = load_settings()
    # The family database (PIN, list of children, helper usage) and one database per child.
    # An older single-child database (tippy.db) is moved into the first child automatically.
    family = Family(settings.db_path.parent, settings.app_language, legacy_db=settings.db_path)
    # PIN: saved (hashed) in the family database after first-run setup or a change; otherwise the optional
    # PARENT_PIN from .env; otherwise the parent is asked to choose one on the first start.
    saved_pin = db.get_settings(family.family_db).get("pin_hash")
    guard = PinGuard(pin=settings.parent_pin or None, stored=saved_pin or None)
    # The online helper is part of the "plus" tier (section 8). Without it Tippy uses its built-in content only.
    if settings.llm_mode == "live" and "ai_extras" not in licence.features(family.data_dir):
        log.info("Online helper not in this licence: using built-in content (LLM_MODE=off)")
        settings = dataclasses.replace(settings, llm_mode="off")
    llm = LLMClient(settings, state_db=family.family_db)
    content = ContentService(family, llm)
    app = FastAPI(title="Tippy", docs_url=None, redoc_url=None, openapi_url=None)
    # launch.py replaces this with a clean shutdown. Standalone fallback below.
    app.state.request_shutdown = lambda: os._exit(0)

    allowed_hosts = {f"127.0.0.1:{PORT}", f"localhost:{PORT}", "testserver"}

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        """Refuse requests that did not come from our own page.

        This stops a website open in another browser tab from talking to Tippy
        ("DNS rebinding" and cross-site requests).
        """
        if request.headers.get("host", "") not in allowed_hosts:
            return JSONResponse({"error": "forbidden"}, status_code=403)
        origin = request.headers.get("origin")
        if origin and origin.split("://", 1)[-1] not in allowed_hosts:
            return JSONResponse({"error": "forbidden"}, status_code=403)
        return await call_next(request)

    @app.middleware("http")
    async def protective_headers(request: Request, call_next):
        """Tell the browser to be strict with our pages, and refuse absurdly large requests.

        The Content-Security-Policy lets the page load only Tippy's own files and talk only to Tippy, so even a
        bug that let foreign text into a page could not run a foreign script or send data anywhere else.
        """
        try:
            too_big = int(request.headers.get("content-length", "0")) > MAX_REQUEST_BYTES
        except ValueError:
            too_big = True
        if too_big:
            return JSONResponse({"error": "too big"}, status_code=413, headers=SECURITY_HEADERS)
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"   # never keep the child's data in a cache
        else:
            # The browser must ask before reusing a saved copy of an app file, so after an update (or when two
            # Tippy versions share one browser profile) it never shows the old screens. Cheap: it's this computer.
            response.headers["Cache-Control"] = "no-cache"
        return response

    @app.exception_handler(Exception)
    async def friendly_error(request: Request, exc: Exception):
        """The child never sees a technical message. Details go to the log."""
        log.exception("Unhandled error on %s", request.url.path)
        return JSONResponse({"error": "oops"}, status_code=500)

    def parent_only(x_parent_token: str | None = Header(default=None)) -> None:
        """Every /api/parent/ endpoint depends on this. It runs BEFORE the request body is read or checked, so
        someone without the PIN token learns nothing, not even what a valid request looks like."""
        if not guard.is_valid_token(x_parent_token):
            raise HTTPException(status_code=401, detail="pin required")

    def confirm_pin(pin: str) -> None:
        """Deleting data needs the PIN typed again (docs/REVAMP_BRIEF.md section 6.4), even with a valid token:
        a parent who walked away from an open parent area should not lose everything to a curious child."""
        if guard.seconds_locked():
            raise HTTPException(status_code=429, detail="locked")
        if guard.verify(pin) is None:
            raise HTTPException(status_code=403, detail="wrong pin")

    # ---------- Child-facing endpoints ----------

    @app.get("/api/settings")
    def read_settings():
        """Settings the child's screen needs. Contains no secrets and nothing from the parent's private data."""
        stored = db.get_settings(family.db_path)
        out = {key: stored.get(key, "") for key in db.CHILD_SETTINGS}
        out["font_scale"] = float(stored.get("font_scale") or 1)
        for flag in ("voice_on", "sound_on", "ask_tippy", "reduce_motion", "has_numpad", "layout_mismatch_flag", "left_handed"):
            out[flag] = stored.get(flag) == "1"
        out["online_helper"] = llm.mode == "live"  # the parent area hides the helper tab when off
        out["setup_needed"] = not guard.has_pin
        out["profile_id"] = family.active_id
        out["profile_count"] = len(family.list())
        out["classroom"] = family.classroom
        out["features"] = sorted(licence.features(family.data_dir))
        out["age_band"] = db.get_age_band(family.db_path)
        for number in ("session_minutes", "daily_limit_minutes"):
            out[number] = int(stored.get(number) or 0)
        return out

    @app.get("/api/languages")
    def list_languages():
        """The languages Tippy speaks (for the pickers and the voice)."""
        return {"languages": languages.public_list(), "keyboards": list(languages.KEYBOARDS)}

    @app.get("/api/mascot/line")
    def mascot_line(event: str = "welcome"):
        return {"text": content.mascot_line(event)}

    @app.get("/api/content/words")
    def practice_words(count: int = Query(default=8, ge=1, le=20), pictured: bool = False,
                       max_len: int = Query(default=4, ge=2, le=10), min_len: int = Query(default=0, ge=0, le=10),
                       theme: str | None = Query(default=None, pattern="^(" + "|".join(bank.THEMES) + ")$")):
        return content.pictured_words(count, max_len, min_len, theme) if pictured else content.words(count)

    @app.get("/api/content/special")
    def special_content(set: str = Query(pattern="^[a-z_]{3,30}$"), count: int = Query(default=5, ge=1, le=10)):
        """Words or sentences that exist for one language only, such as Germany-specific content."""
        found = content.special(set, count)
        if found is None:
            raise HTTPException(status_code=404, detail="no such set for this language")
        return found

    @app.get("/api/pictures")
    def pictures():
        """Word to emoji for the Free Play Studio (Word Woods pictures plus extras)."""
        lang = content.language()
        return {**bank.FREE_PLAY.get(lang, {}), **bank.PICTURES.get(lang, {})}

    class CardBody(BaseModel):
        # The same limit as the Free Play text box (MAX_FREE_CHARS in freeplay.js): letters and spaces only.
        words: str = Field(pattern=r"^[\p{L} ]{1,14}$")

    @app.get("/api/cards")
    def cards():
        """The child's saved Free Play cards, newest first. They never leave this computer."""
        return {"cards": db.list_cards(family.db_path)}

    @app.post("/api/cards")
    def save_card(body: CardBody):
        if not body.words.strip():
            raise HTTPException(status_code=422, detail="empty card")
        db.save_card(family.db_path, body.words.strip())
        return {"cards": db.list_cards(family.db_path)}

    @app.get("/api/content/sentences")
    def practice_sentences(count: int = Query(default=4, ge=1, le=10),
                           kind: str = Query(default="normal", pattern="^(normal|long|question|themed)$")):
        return content.sentences(count, kind)

    class HeartbeatBody(BaseModel):
        seconds: int = Field(ge=0, le=dashboard.MAX_HEARTBEAT_SECONDS)

    @app.post("/api/session/heartbeat")
    def heartbeat(body: HeartbeatBody):
        """The browser reports active play time every 15 seconds (used for break and daily limits)."""
        dashboard.add_play_seconds(family.db_path, body.seconds)
        return dashboard.limits_state(family.db_path)

    @app.get("/api/limits")
    def limits():
        return dashboard.limits_state(family.db_path)

    @app.get("/api/ask")
    def ask_tippy(topic: str = Query(max_length=20)):
        """Picture questions only. Off unless the parent has switched Ask Tippy on."""
        if db.get_settings(family.db_path).get("ask_tippy") != "1":
            raise HTTPException(status_code=403, detail="ask tippy is off")
        return content.ask_answer(topic)

    @app.post("/api/visit")
    def visit():
        """Called when the app opens: counts today as a play day for the streak."""
        family.reset_all_if_new_day(date.today().isoformat(), dashboard.reset_progress)
        progress.record_visit(family.db_path, date.today())
        return {"ok": True}

    @app.get("/api/progress")
    def read_progress():
        return progress.get_progress(family.db_path)

    @app.get("/api/stickers")
    def sticker_catalog():
        return progress.public_catalog()

    class CompleteBody(BaseModel):
        world: str = Field(max_length=20)
        level: int = Field(ge=1, le=20)
        stars: int = Field(ge=0, le=3)

    @app.post("/api/progress/complete")
    def complete_level(body: CompleteBody):
        try:
            return progress.record_completion(family.db_path, body.world, body.level, body.stars)
        except ValueError:
            raise HTTPException(status_code=400, detail="unknown level")

    class KeyEvent(BaseModel):
        key: str = Field(pattern=r"^([A-Z]|[0-9]|SPACE|ENTER|BACKSPACE|SHIFT|UP|DOWN|LEFT|RIGHT|CAPS)$")
        correct: bool
        ms: int = Field(ge=0, le=600000)

    class KeystrokeBody(BaseModel):
        events: list[KeyEvent] = Field(max_length=50)
        adaptive: bool = False  # true only in Letter Land: these presses steer the difficulty

    @app.get("/api/letters")
    def read_letters():
        return difficulty.get_letters(family.db_path)

    @app.post("/api/keystrokes")
    def save_keystrokes(body: KeystrokeBody):
        return difficulty.record_keystrokes(family.db_path, [e.model_dump() for e in body.events], body.adaptive)

    @app.post("/api/layout-mismatch")
    def report_layout_mismatch():
        """The browser calls this (see trackLayoutMismatch in keyboard.js) after several key presses where
        the physical key does not match the chosen keyboard shape (docs/REVAMP_BRIEF.md section 4.4). It
        only sets a flag for the parent area to show next time; it never blocks or slows down the child."""
        db.set_setting(family.db_path, "layout_mismatch_flag", "1")
        return {"ok": True}

    # ---------- Parent endpoints ----------

    class PinBody(BaseModel):
        pin: str = Field(max_length=12)

    @app.post("/api/parent/verify")
    def verify_pin(body: PinBody):
        wait = guard.seconds_locked()
        if wait:
            return JSONResponse({"ok": False, "locked_seconds": wait}, status_code=429)
        token = guard.verify(body.pin)
        if token is None:
            return JSONResponse({"ok": False, "locked_seconds": guard.seconds_locked()}, status_code=401)
        return {"ok": True, "token": token}

    class SetupBody(BaseModel):
        pin: str = Field(pattern=r"^[0-9]{4,8}$")
        language: str = Field(default="en", pattern=languages.LANGUAGE_PATTERN)
        child_name: str = Field(default="", pattern=NAME_PATTERN)
        daily_limit_minutes: int = Field(default=30, ge=0, le=480)
        # Classroom mode (section 6.5): the PIN is the teacher's, and the class starts with this many children.
        classroom: bool = False
        class_size: int = Field(default=1, ge=1, le=30)
        daily_reset: bool = False

    @app.post("/api/setup")
    def first_run_setup(body: SetupBody):
        """Runs once, on the very first start: the parent chooses a PIN and a few basics."""
        if guard.has_pin:
            raise HTTPException(status_code=409, detail="already set up")
        if body.classroom and "classroom" not in licence.features(family.data_dir):
            raise HTTPException(status_code=403, detail="classroom mode needs a school licence")
        db.set_setting(family.family_db, "pin_hash", guard.set_pin(body.pin))
        db.set_setting(family.db_path, "language", body.language)
        db.set_setting(family.db_path, "keyboard_layout", languages.default_keyboard(body.language))
        db.set_setting(family.db_path, "child_name", body.child_name)
        family.rename_active(body.child_name)
        db.set_setting(family.db_path, "daily_limit_minutes", str(body.daily_limit_minutes))
        if body.classroom:
            family.set_classroom(True)
            db.set_setting(family.family_db, "daily_reset", "1" if body.daily_reset else "0")
            db.set_setting(family.family_db, "last_reset_day", date.today().isoformat())
            family.add_anonymous(body.class_size - 1, body.language)
        return read_settings()

    class NewPinBody(BaseModel):
        pin: str = Field(pattern=r"^[0-9]{4,8}$")

    @app.post("/api/parent/pin")
    def change_pin(body: NewPinBody, _parent: None = Depends(parent_only)):
        db.set_setting(family.family_db, "pin_hash", guard.set_pin(body.pin))
        return {"ok": True}  # the old token is revoked: the parent signs in again with the new PIN

    class SettingsBody(BaseModel):
        language: str | None = Field(default=None, pattern=languages.LANGUAGE_PATTERN)
        keyboard_layout: str | None = Field(default=None, pattern=languages.KEYBOARD_PATTERN)
        voice_on: bool | None = None
        sound_on: bool | None = None
        letter_case: str | None = Field(default=None, pattern="^(upper|lower)$")
        # Typed by the child in Sentence Sky. Stored only on this computer, never sent to the LLM.
        child_name: str | None = Field(default=None, pattern=NAME_PATTERN)
        favorite_word: str | None = Field(default=None, pattern=WORD_PATTERN)
        # Up to 8 family words (section 6.1), comma-joined; each one follows the same rule as favorite_word.
        family_words: str | None = Field(default=None, pattern=r"^$|^[\p{L}]{1,15}(,[\p{L}]{1,15}){0,7}$")
        session_minutes: int | None = Field(default=None, ge=0, le=60)
        daily_limit_minutes: int | None = Field(default=None, ge=0, le=480)
        play_window: str | None = Field(default=None, pattern=r"^$|^([0-9]|1[0-9]|2[0-3])-([1-9]|1[0-9]|2[0-4])$")
        # The parent's own word list (section 4.2): up to 20 words, letters only, like every word in a pack.
        custom_words: str | None = Field(default=None, max_length=320, pattern=r"^[\p{L},]*$")
        ask_tippy: bool | None = None
        font_scale: float | None = Field(default=None, ge=1, le=1.25)
        reduce_motion: bool | None = None
        has_numpad: bool | None = None
        left_handed: bool | None = None
        openrouter_model: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._:/\-]{0,80}$")
        interests: list[str] | None = Field(default=None, max_length=4)
        # "5", "6", "7" or "8+" (docs/REVAMP_BRIEF.md section 4.5) - never a birthdate.
        age_band: str | None = Field(default=None, pattern=r"^(5|6|7|8\+)$")
        # The parent dismisses the layout-mismatch note (section 4.4) by setting this back to False.
        layout_mismatch_flag: bool | None = None

    @app.post("/api/parent/settings")
    def update_settings(body: SettingsBody, _parent: None = Depends(parent_only)):
        data = body.model_dump(exclude_none=True)
        words = data.get("custom_words", "").split(",") if data.get("custom_words") else []
        if len(words) > 20 or any(not 1 <= len(word) <= 15 for word in words):
            raise HTTPException(status_code=422, detail="up to 20 words, each 1 to 15 letters")
        if data.get("play_window"):
            start, end = (int(x) for x in data["play_window"].split("-"))
            if start >= end:
                raise HTTPException(status_code=422, detail="the window must start before it ends")
        interests = data.pop("interests", None)
        if interests is not None:
            if not interests or any(topic not in bank.THEMES for topic in interests):
                raise HTTPException(status_code=422, detail="pick at least one known interest")
            with db.connect(family.db_path) as conn:
                conn.execute("UPDATE child_profile SET interests = ? WHERE id = 1", (",".join(dict.fromkeys(interests)),))
        age_band = data.pop("age_band", None)
        if age_band is not None:
            with db.connect(family.db_path) as conn:
                conn.execute("UPDATE child_profile SET age_band = ? WHERE id = 1", (age_band,))
        for key, value in data.items():
            text = "1" if value is True else "0" if value is False else str(value)
            # The helper model belongs to the household; everything else to the child who is selected.
            db.set_setting(family.family_db if key == "openrouter_model" else family.db_path, key, text)
            if key == "child_name":
                family.rename_active(text)
        return read_settings()

    # ---------- Children ----------

    @app.get("/api/profiles")
    def list_profiles():
        """For the "who is playing?" screen. Names stay on this computer."""
        return {"profiles": family.list(), "active": family.active_id, "avatars": AVATARS, "max": family.max_profiles,
                "classroom": family.classroom, "daily_reset": db.get_settings(family.family_db).get("daily_reset") == "1"}

    class SelectBody(BaseModel):
        id: int

    @app.post("/api/profiles/select")
    def select_profile(body: SelectBody):
        """A child taps their picture. No PIN: it only decides whose progress is shown."""
        family.reset_all_if_new_day(date.today().isoformat(), dashboard.reset_progress)
        try:
            family.select(body.id)
        except ProfileError as error:
            raise HTTPException(status_code=422, detail=str(error))
        return read_settings()

    class ClassBody(BaseModel):
        classroom: bool | None = None
        daily_reset: bool | None = None
        add: int = Field(default=0, ge=0, le=30)          # add this many anonymous children

    @app.post("/api/parent/class")
    def update_class(body: ClassBody, _parent: None = Depends(parent_only)):
        if body.classroom is False and len(family.list()) > profiles_module.MAX_PROFILES:
            raise HTTPException(status_code=422, detail=f"Remove children first: home mode has up to {profiles_module.MAX_PROFILES}.")
        if body.classroom and not family.classroom and "classroom" not in licence.features(family.data_dir):
            raise HTTPException(status_code=403, detail="classroom mode needs a school licence")
        if body.classroom is not None:
            family.set_classroom(body.classroom)
        if body.daily_reset is not None:
            db.set_setting(family.family_db, "daily_reset", "1" if body.daily_reset else "0")
            db.set_setting(family.family_db, "last_reset_day", date.today().isoformat())   # starts counting from tomorrow
        family.add_anonymous(body.add, db.get_settings(family.db_path).get("language"))
        return list_profiles()

    @app.get("/api/parent/class/overview")
    def class_overview(_parent: None = Depends(parent_only)):
        """For the teacher's class overview: how far each child is, per world (the browser groups worlds into stages)."""
        children = []
        for profile in family.list():
            state = progress.get_progress(family.path_for(profile["id"]))
            children.append({**profile, "worlds": progress.world_counts(state), "stars": state["total_stars"]})
        return {"children": children}

    class ConsentBody(BaseModel):
        on: bool

    @app.post("/api/parent/ai-consent")
    def ai_consent(body: ConsentBody, _parent: None = Depends(parent_only)):
        """The parent's yes (or no) to the online helper, after the consent screen. Household-wide."""
        db.set_setting(family.family_db, "ai_consent", "1" if body.on else "0")
        log.info("Online helper %s by the parent", "switched on" if body.on else "switched off")
        return llm.status()

    @app.post("/api/parent/licence")
    async def install_licence(request: Request, _parent: None = Depends(parent_only)):
        """The parent picks the licence file they were given; it is checked here and kept in the data folder."""
        try:
            data = json.loads(await request.body())
            payload = licence.verify(data)
        except (ValueError, licence.LicenceError) as error:
            raise HTTPException(status_code=422, detail=str(error) if isinstance(error, licence.LicenceError) else "not-a-licence")
        (family.data_dir / licence.FILE_NAME).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        log.info("Licence installed: %s", ", ".join(payload["tiers"]))
        return {"features": sorted(licence.features(family.data_dir)), "tiers": payload["tiers"], "issued_to": payload.get("issued_to", "")}

    @app.get("/api/parent/licence")
    def licence_status(_parent: None = Depends(parent_only)):
        found = licence.read(family.data_dir)
        return {"features": sorted(licence.features(family.data_dir)), "tiers": found["tiers"] if found else [],
                "issued_to": found.get("issued_to", "") if found else "", "dev_unlock": licence.dev_unlock()}

    class NewProfileBody(BaseModel):
        name: str = Field(min_length=1, pattern=NAME_PATTERN)
        avatar: str = Field(max_length=8)
        language: str | None = Field(default=None, pattern=languages.LANGUAGE_PATTERN)

    @app.post("/api/parent/profiles")
    def add_profile(body: NewProfileBody, _parent: None = Depends(parent_only)):
        try:
            family.create(body.name, body.avatar, body.language)
        except ProfileError as error:
            raise HTTPException(status_code=422, detail=str(error))
        return list_profiles()

    class EditProfileBody(BaseModel):
        name: str | None = Field(default=None, min_length=1, pattern=NAME_PATTERN)
        avatar: str | None = Field(default=None, max_length=8)

    @app.post("/api/parent/profiles/{profile_id}")
    def edit_profile(profile_id: int, body: EditProfileBody, _parent: None = Depends(parent_only)):
        try:
            family.update(profile_id, body.name, body.avatar)
        except ProfileError as error:
            raise HTTPException(status_code=422, detail=str(error))
        return list_profiles()

    class DeleteProfileBody(BaseModel):
        confirm: str
        pin: str = Field(default="", max_length=12)

    @app.post("/api/parent/profiles/{profile_id}/delete")
    def delete_profile(profile_id: int, body: DeleteProfileBody, _parent: None = Depends(parent_only)):
        if body.confirm != "DELETE":
            raise HTTPException(status_code=422, detail="type DELETE to confirm")
        confirm_pin(body.pin)
        try:
            family.delete(profile_id)
        except ProfileError as error:
            raise HTTPException(status_code=422, detail=str(error))
        return list_profiles()

    class UnlockBody(BaseModel):
        world: str = Field(max_length=20)

    @app.post("/api/parent/unlock")
    def unlock(body: UnlockBody, _parent: None = Depends(parent_only)):
        try:
            progress.unlock_world(family.db_path, body.world)
        except ValueError:
            raise HTTPException(status_code=400, detail="unknown world")
        return progress.get_progress(family.db_path)

    @app.get("/api/parent/status")
    def parent_status(_parent: None = Depends(parent_only)):
        return llm.status()

    @app.post("/api/parent/llm/test")
    def test_llm(_parent: None = Depends(parent_only)):
        """The "Test connection" button: one tiny real request."""
        return llm.test_connection()

    @app.get("/api/parent/dashboard")
    def parent_dashboard(_parent: None = Depends(parent_only)):
        return dashboard.dashboard(family.db_path)

    @app.get("/api/parent/summary")
    def parent_summary(refresh: bool = False, _parent: None = Depends(parent_only)):
        """The weekly summary. May take a few seconds when it has to ask the LLM; parent area only."""
        return summary.get_summary(family.db_path, llm, refresh=refresh)

    @app.get("/api/parent/export")
    def parent_export(_parent: None = Depends(parent_only)):
        return dashboard.export_data(family.db_path)

    @app.post("/api/parent/import")
    async def import_backup(request: Request, target: str = Query(default="current", pattern="^(current|new)$"),
                            _parent: None = Depends(parent_only)):
        """Restore a backup file into the child who is shown (`current`) or into a new child (`new`)."""
        raw = await request.body()
        if len(raw) > restore.MAX_BACKUP_BYTES:
            raise HTTPException(status_code=413, detail="too-big")
        try:
            plan = restore.prepare(json.loads(raw))       # everything is checked before anything is changed
        except (ValueError, RecursionError) as error:      # json errors are ValueErrors too
            raise HTTPException(status_code=422, detail=str(error) if isinstance(error, restore.RestoreError) else "bad-file")
        try:
            if target == "new":
                child = family.create(restore.suggested_name(plan) or "Restored", AVATARS[len(family.list()) % len(AVATARS)],
                                      plan["settings"].get("language"))
                path = family.path_for(child["id"])
            else:
                path = family.db_path
            result = restore.apply(path, plan)
        except ProfileError as error:
            raise HTTPException(status_code=422, detail=str(error))
        if target == "current" and plan["settings"].get("child_name") is not None:
            family.rename_active(plan["settings"]["child_name"])
        log.info("Backup restored (%s): %s", target, result["restored"])
        return {**result, "target": target}

    class ResetBody(BaseModel):
        confirm: str
        pin: str = Field(default="", max_length=12)

    @app.post("/api/parent/reset")
    def parent_reset(body: ResetBody, _parent: None = Depends(parent_only)):
        if body.confirm != "RESET":
            raise HTTPException(status_code=400, detail="confirmation missing")
        confirm_pin(body.pin)
        dashboard.reset_progress(family.db_path)
        log.info("Progress reset from parent area")
        return {"ok": True}

    @app.post("/api/parent/delete-everything")
    def delete_everything(body: ResetBody, _parent: None = Depends(parent_only)):
        """Every child, every copy and the PIN are erased; Tippy starts again as a fresh install."""
        if body.confirm != "DELETE EVERYTHING":
            raise HTTPException(status_code=400, detail="confirmation missing")
        confirm_pin(body.pin)
        family.erase_everything()
        guard.forget()
        log.info("Everything deleted from parent area")
        return {"ok": True}

    @app.post("/api/parent/exit")
    def exit_app(_parent: None = Depends(parent_only)):
        """Stop the whole app. Needs the PIN token."""
        log.info("Exit requested from parent area")
        # Wait a moment so this reply reaches the browser before the server stops.
        threading.Timer(0.5, app.state.request_shutdown).start()
        return {"ok": True}

    # Must come last: serves index.html, css, js, fonts.
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    return app


_app = None


def __getattr__(name):
    """`from backend.app import app` creates the app the first time it is asked for.

    It is not created when this module is merely imported (for example by the tests), because
    creating it opens the real data folder.
    """
    global _app
    if name == "app":
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(name)
