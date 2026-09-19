"""The Tippy web server (FastAPI).

It only listens on 127.0.0.1, so nobody else on the network can reach it.
It serves the frontend files and a few small JSON endpoints under /api.
"""
import logging
import os
import threading

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from datetime import date

from backend import db, difficulty, progress
from backend.config import FRONTEND_DIR, LOG_DIR, PORT, load_settings
from backend.content import ContentService
from backend.llm.client import LLMClient
from backend.security import PinGuard

LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_DIR / "tippy.log", encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("tippy")


def create_app() -> FastAPI:
    settings = load_settings()
    db.init_db(settings.db_path, settings.app_language)
    guard = PinGuard(settings.parent_pin)
    llm = LLMClient(settings)
    content = ContentService(settings.db_path, llm)
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
        """Settings the child's screen needs. Contains no secrets."""
        stored = db.get_settings(settings.db_path)
        return {**stored, "voice_on": stored["voice_on"] == "1", "sound_on": stored["sound_on"] == "1"}

    @app.get("/api/mascot/line")
    def mascot_line(event: str = "welcome"):
        return {"text": content.mascot_line(event)}

    @app.get("/api/content/words")
    def practice_words(count: int = Query(default=8, ge=1, le=20), pictured: bool = False,
                       max_len: int = Query(default=4, ge=2, le=6)):
        return content.pictured_words(count, max_len) if pictured else content.words(count)

    @app.get("/api/content/sentences")
    def practice_sentences(count: int = Query(default=4, ge=1, le=10)):
        return content.sentences(count)

    @app.post("/api/visit")
    def visit():
        """Called when the app opens: counts today as a play day for the streak."""
        progress.record_visit(settings.db_path, date.today())
        return {"ok": True}

    @app.get("/api/progress")
    def read_progress():
        return progress.get_progress(settings.db_path)

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
            return progress.record_completion(settings.db_path, body.world, body.level, body.stars)
        except ValueError:
            raise HTTPException(status_code=400, detail="unknown level")

    class KeyEvent(BaseModel):
        key: str = Field(pattern=r"^([A-Z]|SPACE|ENTER|BACKSPACE|SHIFT)$")
        correct: bool
        ms: int = Field(ge=0, le=600000)

    class KeystrokeBody(BaseModel):
        events: list[KeyEvent] = Field(max_length=50)
        adaptive: bool = False  # true only in Letter Land: these presses steer the difficulty

    @app.get("/api/letters")
    def read_letters():
        return difficulty.get_letters(settings.db_path)

    @app.post("/api/keystrokes")
    def save_keystrokes(body: KeystrokeBody):
        return difficulty.record_keystrokes(settings.db_path, [e.model_dump() for e in body.events], body.adaptive)

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

    class SettingsBody(BaseModel):
        language: str | None = Field(default=None, pattern="^(en|de)$")
        keyboard_layout: str | None = Field(default=None, pattern="^(qwerty|qwertz)$")
        voice_on: bool | None = None
        sound_on: bool | None = None
        letter_case: str | None = Field(default=None, pattern="^(upper|lower)$")
        # Typed by the child in Sentence Sky. Stored only on this computer, never sent to the LLM.
        child_name: str | None = Field(default=None, pattern="^[A-Za-zÄÖÜäöüß \\-]{0,20}$")
        favorite_word: str | None = Field(default=None, pattern="^[A-Za-zÄÖÜäöüß]{0,15}$")

    @app.post("/api/parent/settings")
    def update_settings(body: SettingsBody, x_parent_token: str | None = Header(default=None)):
        require_parent(x_parent_token)
        for key, value in body.model_dump(exclude_none=True).items():
            db.set_setting(settings.db_path, key, ("1" if value else "0") if isinstance(value, bool) else value)
        return read_settings()

    class UnlockBody(BaseModel):
        world: str = Field(max_length=20)

    @app.post("/api/parent/unlock")
    def unlock(body: UnlockBody, x_parent_token: str | None = Header(default=None)):
        require_parent(x_parent_token)
        try:
            progress.unlock_world(settings.db_path, body.world)
        except ValueError:
            raise HTTPException(status_code=400, detail="unknown world")
        return progress.get_progress(settings.db_path)

    @app.get("/api/parent/status")
    def parent_status(x_parent_token: str | None = Header(default=None)):
        require_parent(x_parent_token)
        return llm.status()

    @app.post("/api/parent/llm/test")
    def test_llm(x_parent_token: str | None = Header(default=None)):
        """The "Test connection" button: one tiny real request."""
        require_parent(x_parent_token)
        return llm.test_connection()

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


app = create_app()
