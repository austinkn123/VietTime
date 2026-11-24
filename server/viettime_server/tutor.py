"""One conversation turn at a time: hear Austin, ask the brain, speak the reply, save the text."""

import hashlib
import random
import threading
import uuid
from dataclasses import asdict
from pathlib import Path

from .personas import PERSONAS, Persona
from .prompts import build_messages


class TutorError(Exception):
    """An error the app should show. status is the HTTP status the API returns."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class Tutor:
    HISTORY_MESSAGES = 12  # the last 6 back-and-forths go to the brain; older turns are dropped
    KEEP_AUDIO_FILES = 300
    MIN_SECONDS = 0.4  # shorter clips are a slipped finger, and Whisper invents text for them

    def __init__(self, ears, brain, voice, store, audio_dir: Path, log=print):
        self.ears, self.brain, self.voice, self.store = ears, brain, voice, store
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.log = log
        # One GPU and one Austin: run one turn at a time.
        self._lock = threading.Lock()

    # Sessions

    def new_session(self, topic: str | None) -> dict:
        if topic is None:
            last = self.store.last_persona()
            topic = random.choice([k for k in PERSONAS if k != last] or list(PERSONAS))
        if topic not in PERSONAS:
            raise TutorError(404, f"Unknown topic: {topic}")
        return self.session_view(self.store.create_session(topic))

    def session_view(self, session: dict) -> dict:
        return {
            "id": session["id"],
            "persona": persona_view(PERSONAS[session["persona_key"]]),
            "started_at": session["started_at"],
            "ended_at": session["ended_at"],
            "turn_count": session.get("turn_count", 0),
        }

    def _session(self, session_id: int, open_only: bool = True) -> tuple[dict, Persona]:
        session = self.store.get_session(session_id)
        if session is None:
            raise TutorError(404, "That conversation doesn't exist.")
        if open_only and session["ended_at"]:
            raise TutorError(409, "That conversation has already ended.")
        return session, PERSONAS[session["persona_key"]]

    def history(self, session_id: int) -> list[dict]:
        turns = self.store.turns(session_id)[-self.HISTORY_MESSAGES :]
        return [{"role": "user" if t["role"] == "learner" else "assistant", "content": t["text"]} for t in turns]

    # Turns

    def open(self, session_id: int) -> dict:
        """The tutor speaks first."""
        session, persona = self._session(session_id)
        with self._lock:
            if self.store.turns(session_id):
                raise TutorError(409, "The conversation has already started.")
            return self._reply(session_id, persona, None, {})

    def hear(self, session_id: int, audio_path: Path) -> dict:
        import soundfile as sf

        _, persona = self._session(session_id)
        try:
            info = sf.info(str(audio_path))
        except Exception as e:
            raise TutorError(415, f"Couldn't read that recording ({type(e).__name__}).") from e
        if info.frames < self.MIN_SECONDS * info.samplerate:
            raise TutorError(422, "Didn't catch that. Hold the button while you talk.")
        with self._lock:
            try:
                heard, ears_s = self.ears.transcribe(audio_path)
            except Exception as e:
                raise TutorError(500, f"The ears failed: {type(e).__name__}: {e}") from e
            heard = heard.strip()
            if not heard:
                raise TutorError(422, "Didn't catch that. Hold the button while you talk.")
            return self._reply(session_id, persona, heard, {"ears": round(ears_s, 2)})

    def read(self, session_id: int, text: str) -> dict:
        _, persona = self._session(session_id)
        text = text.strip()
        if not text:
            raise TutorError(422, "Nothing to send.")
        with self._lock:
            return self._reply(session_id, persona, text, {})

    def _reply(self, session_id: int, persona: Persona, learner_text: str | None, timings: dict) -> dict:
        messages = build_messages(persona, self.history(session_id), learner_text)
        answer = None
        for _ in range(2):  # a local model now and then returns broken JSON; one retry fixes most
            try:
                answer = self.brain.respond(messages)
            except Exception as e:
                raise TutorError(503, f"The brain isn't answering: {e}") from e
            if not answer.error:
                break
            self.log(f"  brain gave a bad reply ({answer.error}); retrying")
        if answer.error:
            raise TutorError(502, f"The brain gave a bad reply twice ({answer.error}). Try again.")
        timings["brain"] = round(answer.seconds, 2)

        audio_url, voice_error = None, None
        try:
            audio_url, timings["voice"] = self._speak(answer.reply, persona)
        except Exception as e:  # text still helps when the voice fails
            voice_error = f"{type(e).__name__}: {e}"
            self.log(f"  voice failed: {voice_error}")
        timings["total"] = round(sum(v for k, v in timings.items() if k != "total"), 2)

        if learner_text is not None:
            self.store.add_turn(session_id, "learner", learner_text)
        turn = self.store.add_turn(session_id, "tutor", answer.reply, answer.corrections, answer.new_words, timings)
        self.log(f"  session {session_id}: heard {learner_text!r} -> {answer.reply!r} {timings}")
        return {
            "heard": learner_text,
            "reply": answer.reply,
            "audio_url": audio_url,
            "voice_error": voice_error,
            "corrections": answer.corrections,
            "new_words": answer.new_words,
            "timings": timings,
            "turn_id": turn["id"],
        }

    def _speak(self, text: str, persona: Persona, cache: bool = False) -> tuple[str, float]:
        if cache:
            name = hashlib.sha1(f"{persona.voice}|{text}".encode()).hexdigest()[:16] + ".wav"
            if (self.audio_dir / name).exists():
                return f"/audio/{name}", 0.0
        else:
            name = f"{uuid.uuid4().hex[:16]}.wav"
        seconds = self.voice.speak(text, persona.voice, self.audio_dir / name)
        self._prune_audio()
        return f"/audio/{name}", round(seconds, 2)

    def _prune_audio(self) -> None:
        files = sorted(self.audio_dir.glob("*.wav"), key=lambda p: p.stat().st_mtime)
        for old in files[: max(0, len(files) - self.KEEP_AUDIO_FILES)]:
            old.unlink(missing_ok=True)

    def speak(self, text: str, topic: str) -> str:
        """Speak any text in a persona's voice, e.g. a better phrasing in the recap."""
        if topic not in PERSONAS:
            raise TutorError(404, f"Unknown topic: {topic}")
        text = text.strip()
        if not text:
            raise TutorError(422, "Nothing to say.")
        with self._lock:
            return self._speak(text, PERSONAS[topic], cache=True)[0]

    # End and recap

    def end(self, session_id: int) -> dict:
        self._session(session_id, open_only=False)
        self.store.end_session(session_id)
        return self.transcript(session_id)

    def transcript(self, session_id: int) -> dict:
        session, persona = self._session(session_id, open_only=False)
        turns = self.store.turns(session_id)
        return {
            "session": self.session_view({**session, "turn_count": len(turns)}),
            "turns": [
                {"role": t["role"], "text": t["text"], "corrections": t["corrections"], "new_words": t["new_words"], "created_at": t["created_at"]}
                for t in turns
            ],
            "recap": recap(turns),
        }

    def sessions(self) -> list[dict]:
        """Past conversations, newest first, leaving out ones where nobody said anything."""
        return [self.session_view(s) for s in self.store.list_sessions() if s["turn_count"]]


def recap(turns: list[dict]) -> dict:
    """Every quiet correction and new word from the conversation, without repeats."""
    corrections, words = [], []
    seen_fixes, seen_words = set(), set()
    learner_lines = 0
    last_learner = None
    for t in turns:
        if t["role"] == "learner":
            learner_lines += 1
            last_learner = t["text"]
            continue
        for c in t["corrections"]:
            key = (c.get("said", "").casefold(), c.get("better", "").casefold())
            if key not in seen_fixes and c.get("better"):
                seen_fixes.add(key)
                corrections.append({**c, "in": last_learner})
        for w in t["new_words"]:
            key = w.get("word", "").casefold()
            if key and key not in seen_words:
                seen_words.add(key)
                words.append(w)
    return {"learner_turns": learner_lines, "corrections": corrections, "new_words": words}


def persona_view(p: Persona) -> dict:
    """What the app shows. Descriptions are written for the tutor ("Austin's aunt"), so turn them toward Austin."""
    view = {k: v for k, v in asdict(p).items() if k in ("key", "topic", "name", "description", "austin_calls_them", "austin_self")}
    view["description"] = p.description.replace("Austin's", "your").replace("Austin", "you")
    return view
