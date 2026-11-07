"""Ears, brain and voice.

Each part sits behind a small class, so a different model can replace one part
without touching the others (fakes.py has stand-ins with the same methods).
Heavy libraries are imported inside the classes, so the server's practice mode
and `python -m step0 check` work without them installed.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .prompts import REPLY_SCHEMA

TARGET_SR = 16_000


def load_audio_16k(path: Path):
    """Read a WAV file as mono float32 at 16 kHz, the rate PhoWhisper expects."""
    import numpy as np
    import soundfile as sf
    import soxr

    audio, sr = sf.read(str(path), dtype="float32", always_2d=True)
    audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        audio = soxr.resample(audio, sr, TARGET_SR)
    return audio.astype(np.float32)


class Ears:
    """Speech to text with PhoWhisper, a Whisper model fine-tuned on Vietnamese."""

    MAX_SECONDS = 30  # Whisper reads at most 30 s per pass; push-to-talk turns are shorter

    def __init__(self, model_id: str, device: str):
        import torch
        from transformers import WhisperForConditionalGeneration, WhisperProcessor

        self._torch = torch
        self.device = device
        self.processor = WhisperProcessor.from_pretrained(model_id)
        model = WhisperForConditionalGeneration.from_pretrained(model_id)
        if device.startswith("cuda"):
            model = model.half()
        self.model = model.to(device).eval()

    def transcribe(self, path: Path) -> tuple[str, float]:
        start = time.perf_counter()
        audio = load_audio_16k(path)[: self.MAX_SECONDS * TARGET_SR]
        feats = self.processor(audio, sampling_rate=TARGET_SR, return_tensors="pt").input_features
        feats = feats.to(self.device, dtype=self.model.dtype)
        with self._torch.inference_mode():
            try:
                ids = self.model.generate(feats, language="vi", task="transcribe", max_new_tokens=220)
            except (ValueError, KeyError, TypeError):
                # Some fine-tunes drop Whisper's language table; let it auto-detect.
                ids = self.model.generate(feats, max_new_tokens=220)
        text = self.processor.batch_decode(ids, skip_special_tokens=True)[0].strip()
        return text, time.perf_counter() - start


class OllamaError(RuntimeError):
    pass


@dataclass
class BrainReply:
    reply: str
    corrections: list = field(default_factory=list)
    new_words: list = field(default_factory=list)
    seconds: float = 0.0
    raw: str = ""
    error: str | None = None


class Brain:
    """The tutor: a local model served by Ollama, answering in a fixed JSON shape."""

    def __init__(self, model: str, host: str = "http://127.0.0.1:11434", timeout: float = 300):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        # Qwen3 thinks before answering unless told not to, which costs seconds per
        # reply. Models without a thinking mode reject the flag, so drop it then.
        self._send_think = True

    def _chat(self, messages: list[dict], fmt=None, options: dict | None = None) -> str:
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": "30m",
            "options": {"temperature": 0.6, "num_ctx": 4096, **(options or {})},
        }
        if fmt is not None:
            body["format"] = fmt
        if self._send_think:
            body["think"] = False
        r = requests.post(f"{self.host}/api/chat", json=body, timeout=self.timeout)
        if r.status_code == 400 and "think" in r.text.lower() and self._send_think:
            self._send_think = False
            return self._chat(messages, fmt, options)
        if r.status_code != 200:
            raise OllamaError(f"Ollama returned {r.status_code}: {r.text[:300]}")
        return r.json()["message"]["content"]

    def warm(self) -> float:
        """Load the model into memory; returns how long that took."""
        start = time.perf_counter()
        self._chat([{"role": "user", "content": "Xin chào"}], options={"num_predict": 1})
        return time.perf_counter() - start

    def respond(self, messages: list[dict]) -> BrainReply:
        start = time.perf_counter()
        raw = self._chat(messages, fmt=REPLY_SCHEMA)
        seconds = time.perf_counter() - start
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            return BrainReply("", seconds=seconds, raw=raw, error=f"invalid JSON: {e}")
        reply = data.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            return BrainReply("", seconds=seconds, raw=raw, error="no reply text")
        return BrainReply(
            reply=reply.strip(),
            corrections=data.get("corrections") or [],
            new_words=data.get("new_words") or [],
            seconds=seconds,
            raw=raw,
        )

    def gpu_share(self) -> float | None:
        """Fraction of the loaded model that sits in GPU memory (1.0 = all of it)."""
        try:
            r = requests.get(f"{self.host}/api/ps", timeout=10)
            r.raise_for_status()
        except requests.RequestException:
            return None
        for m in r.json().get("models", []):
            if m.get("name") == self.model or m.get("model") == self.model:
                size = m.get("size") or 0
                return (m.get("size_vram") or 0) / size if size else None
        return None


class Voice:
    """Text to speech with VieNeu-TTS v3 Turbo (ONNX on CPU, PyTorch on a GPU)."""

    def __init__(self, device: str):
        from vieneu import Vieneu

        self.tts = Vieneu(device=device)

    def has_voice(self, name: str) -> bool:
        return self.tts.resolve_voice_name(name) is not None

    def speak(self, text: str, voice: str, out_path: Path) -> float:
        start = time.perf_counter()
        audio = self.tts.infer(text, voice=voice)
        self.tts.save(audio, str(out_path))
        return time.perf_counter() - start

    def close(self) -> None:
        self.tts.close()
