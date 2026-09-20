"""The Tippy web server (FastAPI).

It only listens on 127.0.0.1, so nobody else on the network can reach it.
It serves the frontend files and a few small JSON endpoints under /api.
"""
import json
import logging
import os
import threading

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from datetime import date

from backend import bank, dashboard, db, difficulty, languages, progress, restore, summary
from backend.config import FRONTEND_DIR, LOG_DIR, PORT, load_settings
from backend.content import ContentService
from backend.llm.client import LLMClient
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


def create_app() -> FastAPI:
    settings = load_settings()
    # The family database (PIN, list of children, helper usage) and one database per child.
    # An older single-child database (tippy.db) is moved into the first child automatically.
    family = Family(settings.db_path.parent, settings.app_language, legacy_db=settings.db_path)
    # PIN: saved (hashed) in the family database after first-run setup or a change; otherwise the optional
    # PARENT_PIN from .env; otherwise the parent is asked to choose one on the first start.
    saved_pin = db.get_settings(family.family_db).get("pin_hash")
    guard = PinGuard(pin=settings.parent_pin or None, stored=saved_pin or None)
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

    @app.exception_handler(Exception)
    async def friendly_error(request: Request, exc: Exception):
        """The child never sees a technical message. Details go to the log."""
        log.exception("Unhandled error on %s", request.url.path)
        return JSONResponse({"error": "oops"}, status_code=500)

    def require_parent(token: str | None) -> None:
        if not guard.is_valid_token(token):
            raise HTTPException(status_code=401, detail="pin required")

    # ---------- Child-facing endpoints ----------

    @app.get("/api/settings")
    def read_settings():
        """Settings the child's screen needs. Contains no secrets and nothing from the parent's private data."""
        stored = db.get_settings(family.db_path)
        out = {key: stored.get(key, "") for key in db.CHILD_SETTINGS}
        out["font_scale"] = float(stored.get("font_scale") or 1)
        for flag in ("voice_on", "sound_on", "ask_tippy", "reduce_motion", "has_numpad"):
            out[flag] = stored.get(flag) == "1"
        out["online_helper"] = llm.mode == "live"  # the parent area hides the helper tab when off
        out["setup_needed"] = not guard.has_pin
        out["profile_id"] = family.active_id
        out["profile_count"] = len(family.list())
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

    @app.post("/api/setup")
    def first_run_setup(body: SetupBody):
        """Runs once, on the very first start: the parent chooses a PIN and a few basics."""
        if guard.has_pin:
            raise HTTPException(status_code=409, detail="already set up")
        db.set_setting(family.family_db, "pin_hash", guard.set_pin(body.pin))
        db.set_setting(family.db_path, "language", body.language)
        db.set_setting(family.db_path, "keyboard_layout", languages.default_keyboard(body.language))
        db.set_setting(family.db_path, "child_name", body.child_name)
        family.rename_active(body.child_name)
        db.set_setting(family.db_path, "daily_limit_minutes", str(body.daily_limit_minutes))
        return read_settings()

    class NewPinBody(BaseModel):
        pin: str = Field(pattern=r"^[0-9]{4,8}$")

    @app.post("/api/parent/pin")
    def change_pin(body: NewPinBody, x_parent_token: str | None = Header(default=None)):
        require_parent(x_parent_token)
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
        session_minutes: int | None = Field(default=None, ge=0, le=60)
        daily_limit_minutes: int | None = Field(default=None, ge=0, le=480)
        ask_tippy: bool | None = None
        font_scale: float | None = Field(default=None, ge=1, le=1.25)
        reduce_motion: bool | None = None
        has_numpad: bool | None = None
        openrouter_model: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._:/\-]{0,80}$")
        interests: list[str] | None = Field(default=None, max_length=4)

    @app.post("/api/parent/settings")
    def update_settings(body: SettingsBody, x_parent_token: str | None = Header(default=None)):
        require_parent(x_parent_token)
        data = body.model_dump(exclude_none=True)
        interests = data.pop("interests", None)
        if interests is not None:
            if not interests or any(topic not in bank.THEMES for topic in interests):
                raise HTTPException(status_code=422, detail="pick at least one known interest")
            with db.connect(family.db_path) as conn:
                conn.execute("UPDATE child_profile SET interests = ? WHERE id = 1", (",".join(dict.fromkeys(interests)),))
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
        return {"profiles": family.list(), "active": family.active_id, "avatars": AVATARS}

    class SelectBody(BaseModel):
        id: int

    @app.post("/api/profiles/select")
    def select_profile(body: SelectBody):
        """A child taps their picture. No PIN: it only decides whose progress is shown."""
        try:
            family.select(body.id)
        except ProfileError as error:
            raise HTTPException(status_code=422, detail=str(error))
        return read_settings()

    class NewProfileBody(BaseModel):
        name: str = Field(min_length=1, pattern=NAME_PATTERN)
        avatar: str = Field(max_length=8)
        language: str | None = Field(default=None, pattern=languages.LANGUAGE_PATTERN)

    @app.post("/api/parent/profiles")
    def add_profile(body: NewProfileBody, x_parent_token: str | None = Header(default=None)):
        require_parent(x_parent_token)
        try:
            family.create(body.name, body.avatar, body.language)
        except ProfileError as error:
            raise HTTPException(status_code=422, detail=str(error))
        return list_profiles()

    class EditProfileBody(BaseModel):
        name: str | None = Field(default=None, min_length=1, pattern=NAME_PATTERN)
        avatar: str | None = Field(default=None, max_length=8)

    @app.post("/api/parent/profiles/{profile_id}")
    def edit_profile(profile_id: int, body: EditProfileBody, x_parent_token: str | None = Header(default=None)):
        require_parent(x_parent_token)
        try:
            family.update(profile_id, body.name, body.avatar)
        except ProfileError as error:
            raise HTTPException(status_code=422, detail=str(error))
        return list_profiles()

    class DeleteProfileBody(BaseModel):
        confirm: str

    @app.post("/api/parent/profiles/{profile_id}/delete")
    def delete_profile(profile_id: int, body: DeleteProfileBody, x_parent_token: str | None = Header(default=None)):
        require_parent(x_parent_token)
        if body.confirm != "DELETE":
            raise HTTPException(status_code=422, detail="type DELETE to confirm")
        try:
            family.delete(profile_id)
        except ProfileError as error:
            raise HTTPException(status_code=422, detail=str(error))
        return list_profiles()

    class UnlockBody(BaseModel):
        world: str = Field(max_length=20)

    @app.post("/api/parent/unlock")
    def unlock(body: UnlockBody, x_parent_token: str | None = Header(default=None)):
        require_parent(x_parent_token)
        try:
            progress.unlock_world(family.db_path, body.world)
        except ValueError:
            raise HTTPException(status_code=400, detail="unknown world")
        return progress.get_progress(family.db_path)

    @app.get("/api/parent/status")
    def parent_status(x_parent_token: str | None = Header(default=None)):
        require_parent(x_parent_token)
        return llm.status()

    @app.post("/api/parent/llm/test")
    def test_llm(x_parent_token: str | None = Header(default=None)):
        """The "Test connection" button: one tiny real request."""
        require_parent(x_parent_token)
        return llm.test_connection()

    @app.get("/api/parent/dashboard")
    def parent_dashboard(x_parent_token: str | None = Header(default=None)):
        require_parent(x_parent_token)
        return dashboard.dashboard(family.db_path)

    @app.get("/api/parent/summary")
    def parent_summary(refresh: bool = False, x_parent_token: str | None = Header(default=None)):
        """The weekly summary. May take a few seconds when it has to ask the LLM; parent area only."""
        require_parent(x_parent_token)
        return summary.get_summary(family.db_path, llm, refresh=refresh)

    @app.get("/api/parent/export")
    def parent_export(x_parent_token: str | None = Header(default=None)):
        require_parent(x_parent_token)
        return dashboard.export_data(family.db_path)

    @app.post("/api/parent/import")
    async def import_backup(request: Request, target: str = Query(default="current", pattern="^(current|new)$"),
                            x_parent_token: str | None = Header(default=None)):
        """Restore a backup file into the child who is shown (`current`) or into a new child (`new`)."""
        require_parent(x_parent_token)
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

    @app.post("/api/parent/reset")
    def parent_reset(body: ResetBody, x_parent_token: str | None = Header(default=None)):
        require_parent(x_parent_token)
        if body.confirm != "RESET":
            raise HTTPException(status_code=400, detail="confirmation missing")
        dashboard.reset_progress(family.db_path)
        log.info("Progress reset from parent area")
        return {"ok": True}

    @app.post("/api/parent/exit")
    def exit_app(x_parent_token: str | None = Header(default=None)):
        """Stop the whole app. Needs the PIN token."""
        require_parent(x_parent_token)
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
