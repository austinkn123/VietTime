"""Tests that run without any models: prompts, parsing, the run loop with fake engines, and the report."""

import json
import re
from pathlib import Path

import pytest

import step0.__main__ as cli
from step0 import engines
from step0.engines import Brain
from step0.personas import PERSONAS
from step0.prompts import build_messages, system_prompt
from step0.scenarios import RECORDING_PROMPTS, SCRIPTED

# Region "Nam" presets in VieNeu 3.8.3 assets/voices_v3_turbo.json
SOUTHERN_VOICES = {"Thùy Dung", "Thái Sơn", "Thục Đoan", "Minh Triết", "Mỹ Duyên", "Đức Trí", "Kim Thanh", "Adam"}


def test_every_persona_uses_a_southern_voice():
    assert {p.voice for p in PERSONAS.values()} <= SOUTHERN_VOICES


def test_scenarios_point_at_real_personas():
    for item in [*SCRIPTED, *RECORDING_PROMPTS]:
        assert item.persona in PERSONAS


def test_system_prompt_fills_every_placeholder():
    for p in PERSONAS.values():
        text = system_prompt(p)
        assert not re.search(r"\{[a-z_]+\}", text)
        assert f'call Austin "{p.you_pronoun}"' in text


def test_build_messages_opener_and_history():
    p = PERSONAS["food"]
    opener = build_messages(p, [], None)
    assert opener[0]["role"] == "system" and "Start the conversation" in opener[-1]["content"]
    history = [{"role": "assistant", "content": "Chào em!"}]
    msgs = build_messages(p, history, "Cho em hai cân xoài.")
    assert msgs[1:] == [*history, {"role": "user", "content": "Cho em hai cân xoài."}]


class FakeResponse:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload
        self.text = text or json.dumps(payload)

    def json(self):
        return self._payload


def test_brain_parses_reply(monkeypatch):
    content = {"reply": "Hai ký xoài hả em?", "corrections": [{"said": "hai cân", "better": "hai ký", "why_en": "Southern", "why_vi": "miền Nam"}], "new_words": []}
    sent = {}

    def post(url, json, timeout):
        sent.update(json)
        return FakeResponse(200, {"message": {"content": __import__("json").dumps(content)}})

    monkeypatch.setattr(engines.requests, "post", post)
    answer = Brain("qwen3:8b").respond([{"role": "user", "content": "x"}])
    assert answer.reply == "Hai ký xoài hả em?" and answer.error is None
    assert answer.corrections[0]["better"] == "hai ký"
    assert sent["think"] is False and sent["format"]["required"] == ["reply", "corrections", "new_words"]


def test_brain_drops_think_flag_when_model_rejects_it(monkeypatch):
    calls = []

    def post(url, json, timeout):
        calls.append(dict(json))
        if "think" in json:
            return FakeResponse(400, text='{"error":"model does not support thinking"}')
        return FakeResponse(200, {"message": {"content": '{"reply": "Dạ", "corrections": [], "new_words": []}'}})

    monkeypatch.setattr(engines.requests, "post", post)
    brain = Brain("gemma3:4b")
    assert brain.respond([]).reply == "Dạ"
    assert brain.respond([]).reply == "Dạ"
    assert len(calls) == 3  # one rejected call, then no more think flag


def test_brain_reports_bad_json(monkeypatch):
    monkeypatch.setattr(engines.requests, "post", lambda url, json, timeout: FakeResponse(200, {"message": {"content": "not json"}}))
    answer = Brain("qwen3:8b").respond([])
    assert answer.reply == "" and answer.error.startswith("invalid JSON")


class FakeVoice:
    def __init__(self, device):
        pass

    def has_voice(self, name):
        return name in SOUTHERN_VOICES

    def speak(self, text, voice, out_path):
        Path(out_path).write_bytes(b"RIFF")
        return 1.5

    def close(self):
        pass


class FakeEars:
    def __init__(self, model_id, device):
        pass

    def transcribe(self, path):
        return "Dạ con chào cô, hôm nay con ăn phở | ngon lắm.", 0.8


class FakeBrain:
    def __init__(self, model, host):
        self.model = model

    def warm(self):
        return 2.0

    def gpu_share(self):
        return 1.0

    def respond(self, messages):
        last = messages[-1]["content"]
        fixes = [{"said": "cân", "better": "ký", "why_en": "Southern word", "why_vi": "từ miền Nam"}] if "cân" in last else []
        return engines.BrainReply("Dạ, vậy hả? Rồi sao nữa?", corrections=fixes, seconds=3.0)


def test_run_end_to_end_with_fake_engines(tmp_path, monkeypatch):
    import soundfile as sf
    import numpy as np

    monkeypatch.setattr(cli, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(cli, "RECORDINGS", tmp_path / "recordings")
    (tmp_path / "recordings").mkdir()
    sf.write(str(tmp_path / "recordings" / "01-aunt-food.wav"), np.zeros(16_000, dtype="float32"), 16_000)
    monkeypatch.setattr(engines, "Voice", FakeVoice)
    monkeypatch.setattr(engines, "Ears", FakeEars)
    monkeypatch.setattr(engines, "Brain", FakeBrain)

    assert cli.main(["run", "--limit", "3", "--max-wait", "6"]) == 0

    (run_dir,) = (tmp_path / "results").iterdir()
    results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    turns = results["models"]["qwen3:8b"]["turns"]
    spoken = [t for t in turns if t["kind"] == "spoken"]
    assert len(spoken) == 1 and spoken[0]["total_s"] == pytest.approx(0.8 + 3.0 + 1.5)
    assert len([t for t in turns if t["kind"] == "opener"]) == 3
    assert any(c["better"] == "ký" for t in turns for c in t.get("corrections", []))
    assert not results["errors"]

    report = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "| Fit |" in report and "#### market-weight · Chị Ba" in report
    assert "phở \\| ngon" in report  # pipes inside cells are escaped
    assert "median 4.5 s" in report and "median 5.3 s" in report
