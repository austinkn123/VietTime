"""The whole server through its HTTP API, with the fake engines standing in for the models."""

import io
import json
import wave

import pytest
from fastapi.testclient import TestClient

from viettime_server.api import create_app
from viettime_server.engines import BrainReply
from viettime_server.fakes import FakeBrain, FakeEars, FakeVoice
from viettime_server.personas import PERSONAS
from viettime_server.store import Store
from viettime_server.tutor import Tutor


def wav_bytes(seconds: float, rate: int = 16_000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x01\x00" * int(seconds * rate))
    return buf.getvalue()


@pytest.fixture
def make_client(tmp_path):
    def make(brain=None, ears=None, voice=None):
        tutor = Tutor(ears or FakeEars(), brain or FakeBrain(delay=0), voice or FakeVoice(), Store(tmp_path / "t.db"), tmp_path / "audio", log=lambda *_: None)
        return TestClient(create_app(tutor, {"mode": "fake"})), tutor

    return make


@pytest.fixture
def client(make_client):
    return make_client()[0]


def upload(client, session_id, data: bytes, name="turn.wav"):
    return client.post(f"/api/sessions/{session_id}/turns", files={"audio": (name, data, "audio/wav")})


def test_health_and_topics(client):
    assert client.get("/api/health").json() == {"ok": True, "mode": "fake"}
    topics = client.get("/api/topics").json()
    assert [t["key"] for t in topics] == list(PERSONAS)
    assert "voice" not in topics[0] and topics[0]["austin_calls_them"] == "cô"
    assert topics[0]["description"] == "your aunt who lives in Saigon"


def test_full_conversation(client):
    session = client.post("/api/sessions", json={"topic": "family"}).json()
    sid = session["id"]
    assert session["persona"]["name"] == "Cô Tư"

    opener = client.post(f"/api/sessions/{sid}/open").json()
    assert opener["heard"] is None and "Cô Tư" in opener["reply"]
    audio = client.get(opener["audio_url"])
    assert audio.status_code == 200 and audio.content[:4] == b"RIFF"

    spoken = upload(client, sid, wav_bytes(1.5))
    assert spoken.status_code == 200, spoken.text
    turn = spoken.json()
    assert turn["heard"] == "Dạ, bố mẹ vẫn khoẻ lắm."
    assert "ba má" in turn["reply"]  # the quiet recast
    assert turn["corrections"][0]["better"] == "ba má"
    assert set(turn["timings"]) == {"ears", "brain", "voice", "total"}

    asked = client.post(f"/api/sessions/{sid}/turns/text", json={"text": "How do you say deadline?"}).json()
    assert asked["new_words"] == [{"word": "hạn chót", "meaning_en": "deadline"}]
    client.post(f"/api/sessions/{sid}/turns/text", json={"text": "How do you say deadline?"})  # asked twice

    ended = client.post(f"/api/sessions/{sid}/end").json()
    recap = ended["recap"]
    assert recap["learner_turns"] == 3
    assert recap["corrections"] == [{**turn["corrections"][0], "in": turn["heard"]}]
    assert [w["word"] for w in recap["new_words"]] == ["hạn chót"]  # no repeats
    assert [t["role"] for t in ended["turns"]] == ["tutor", "learner", "tutor", "learner", "tutor", "learner", "tutor"]

    listed = client.get("/api/sessions").json()
    assert listed[0]["id"] == sid and listed[0]["turn_count"] == 7 and listed[0]["ended_at"]
    assert client.get(f"/api/sessions/{sid}").json()["recap"] == recap


def test_history_leaves_out_empty_conversations(client):
    client.post("/api/sessions", json={"topic": "food"})
    assert client.get("/api/sessions").json() == []


def test_learner_can_talk_first(client):
    sid = client.post("/api/sessions", json={"topic": "food"}).json()["id"]
    assert upload(client, sid, wav_bytes(1)).status_code == 200
    assert client.post(f"/api/sessions/{sid}/open").status_code == 409  # too late for the tutor to open


def test_surprise_me_avoids_the_last_persona(client):
    last = client.post("/api/sessions", json={"topic": "news"}).json()["persona"]["key"]
    for _ in range(10):
        nxt = client.post("/api/sessions", json={}).json()["persona"]["key"]
        assert nxt in PERSONAS and nxt != last
        last = nxt


def test_errors_the_app_shows(client):
    assert client.post("/api/sessions", json={"topic": "sports"}).status_code == 404
    assert client.post("/api/sessions/999/open").status_code == 404
    sid = client.post("/api/sessions", json={"topic": "work"}).json()["id"]

    short = upload(client, sid, wav_bytes(0.1))
    assert short.status_code == 422 and "Didn't catch that" in short.json()["detail"]
    assert upload(client, sid, b"not audio at all", "turn.m4a").status_code == 415
    assert client.post(f"/api/sessions/{sid}/turns/text", json={"text": "  "}).status_code == 422
    assert client.get(f"/api/sessions/{sid}").json()["turns"] == []  # failed turns leave no trace

    client.post(f"/api/sessions/{sid}/end")
    assert client.post(f"/api/sessions/{sid}/turns/text", json={"text": "Dạ"}).status_code == 409


class FlakyBrain(FakeBrain):
    def __init__(self, bad_replies: int):
        super().__init__(delay=0)
        self.bad_replies = bad_replies
        self.calls = []

    def respond(self, messages):
        self.calls.append(messages)
        if len(self.calls) <= self.bad_replies:
            return BrainReply("", raw="{", error="invalid JSON")
        return super().respond(messages)


def test_one_bad_brain_reply_is_retried(make_client):
    client, _ = make_client(brain=FlakyBrain(bad_replies=1))
    sid = client.post("/api/sessions", json={"topic": "food"}).json()["id"]
    assert client.post(f"/api/sessions/{sid}/open").status_code == 200


def test_two_bad_brain_replies_fail_cleanly(make_client):
    client, _ = make_client(brain=FlakyBrain(bad_replies=2))
    sid = client.post("/api/sessions", json={"topic": "food"}).json()["id"]
    r = client.post(f"/api/sessions/{sid}/open")
    assert r.status_code == 502 and "bad reply" in r.json()["detail"]


def test_brain_offline_is_a_503(make_client):
    class Offline(FakeBrain):
        def respond(self, messages):
            raise ConnectionError("Ollama not running")

    client, _ = make_client(brain=Offline())
    sid = client.post("/api/sessions", json={"topic": "food"}).json()["id"]
    assert client.post(f"/api/sessions/{sid}/open").status_code == 503


def test_ears_failure_is_a_500_not_a_bad_recording(make_client):
    class Crashing(FakeEars):
        def transcribe(self, path):
            raise RuntimeError("CUDA out of memory")

    client, _ = make_client(ears=Crashing())
    sid = client.post("/api/sessions", json={"topic": "food"}).json()["id"]
    r = upload(client, sid, wav_bytes(1))
    assert r.status_code == 500 and "out of memory" in r.json()["detail"]


def test_voice_failure_still_returns_text(make_client):
    class Broken(FakeVoice):
        def speak(self, text, voice, out_path):
            raise RuntimeError("no GPU memory")

    client, _ = make_client(voice=Broken())
    sid = client.post("/api/sessions", json={"topic": "food"}).json()["id"]
    turn = client.post(f"/api/sessions/{sid}/open").json()
    assert turn["reply"] and turn["audio_url"] is None and "no GPU memory" in turn["voice_error"]


def test_brain_sees_only_recent_history(make_client):
    brain = FlakyBrain(bad_replies=0)
    client, tutor = make_client(brain=brain)
    sid = client.post("/api/sessions", json={"topic": "errands"}).json()["id"]
    for i in range(10):
        client.post(f"/api/sessions/{sid}/turns/text", json={"text": f"câu {i}"})
    last = brain.calls[-1]
    assert last[0]["role"] == "system" and last[-1]["content"] == "câu 9"
    assert len(last) == 1 + tutor.HISTORY_MESSAGES + 1
    assert [m["role"] for m in last[1:3]] == ["user", "assistant"]


def test_speak_caches_by_text(client, tmp_path):
    first = client.post("/api/speak", json={"text": "hai ký xoài", "topic": "food"}).json()["audio_url"]
    again = client.post("/api/speak", json={"text": "hai ký xoài", "topic": "food"}).json()["audio_url"]
    assert first == again and client.get(first).status_code == 200


def test_store_survives_restart(tmp_path):
    store = Store(tmp_path / "t.db")
    s = store.create_session("food")
    store.add_turn(s["id"], "tutor", "Chào em", [{"said": "a", "better": "b"}], [], {"brain": 1.0})
    store.close()
    again = Store(tmp_path / "t.db")
    (turn,) = again.turns(s["id"])
    assert turn["corrections"] == [{"said": "a", "better": "b"}] and json.dumps(turn["timings"]) == '{"brain": 1.0}'
