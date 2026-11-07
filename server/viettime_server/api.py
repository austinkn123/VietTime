"""HTTP API the iPhone app talks to."""

import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .personas import PERSONAS
from .tutor import Tutor, TutorError, persona_view

MAX_UPLOAD_BYTES = 10 * 2**20  # a 30 s WAV at 16 kHz is about 1 MB


class NewSession(BaseModel):
    topic: str | None = None  # None means "surprise me"


class TypedTurn(BaseModel):
    text: str


class SpeakRequest(BaseModel):
    text: str
    topic: str


def create_app(tutor: Tutor, info: dict) -> FastAPI:
    app = FastAPI(title="VietTime")
    # Only reachable on the home network; the app runs from Expo Go, so allow any origin.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(TutorError)
    async def tutor_error(_: Request, e: TutorError):
        return JSONResponse({"detail": e.message}, status_code=e.status)

    @app.get("/api/health")
    def health():
        return {"ok": True, **info}

    @app.get("/api/topics")
    def topics():
        return [persona_view(p) for p in PERSONAS.values()]

    @app.post("/api/sessions")
    def new_session(body: NewSession):
        return tutor.new_session(body.topic)

    @app.get("/api/sessions")
    def sessions():
        return tutor.sessions()

    @app.get("/api/sessions/{session_id}")
    def session(session_id: int):
        return tutor.transcript(session_id)

    @app.post("/api/sessions/{session_id}/open")
    def open_session(session_id: int):
        return tutor.open(session_id)

    @app.post("/api/sessions/{session_id}/turns")
    def spoken_turn(session_id: int, audio: UploadFile = File(...)):
        suffix = Path(audio.filename or "turn.wav").suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            shutil.copyfileobj(audio.file, tmp, length=2**16)
            path = Path(tmp.name)
        try:
            if path.stat().st_size > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "That recording is too long.")
            return tutor.hear(session_id, path)
        finally:
            path.unlink(missing_ok=True)  # Austin's voice is never kept

    @app.post("/api/sessions/{session_id}/turns/text")
    def typed_turn(session_id: int, body: TypedTurn):
        return tutor.read(session_id, body.text)

    @app.post("/api/sessions/{session_id}/end")
    def end_session(session_id: int):
        return tutor.end(session_id)

    @app.post("/api/speak")
    def speak(body: SpeakRequest):
        return {"audio_url": tutor.speak(body.text, body.topic)}

    app.mount("/audio", StaticFiles(directory=tutor.audio_dir), name="audio")
    return app
