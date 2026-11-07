"""Stand-ins for the three models, so the app can be tested on any PC with no GPU and no downloads.

    python -m viettime_server --fake

The server still checks your recording is real audio, but the fake ears always
"hear" one of a few canned sentences. The fake brain fixes a short
list of Northern words, and the fake voice plays beeps instead of speech.
"""

import array
import math
import re
import time
import wave
from itertools import cycle
from pathlib import Path

from .engines import BrainReply

# What the fake ears "hear", in turn. Each has a mistake the fake brain catches.
SAMPLE_HEARD = [
    "Dạ, bố mẹ vẫn khoẻ lắm.",
    "Hôm nay em muốn mua hai cân xoài.",
    "How do you say deadline?",
    "Cái này đắt quá, em không mua đâu.",
    "Tui hơi mệt vì tuần này làm việc nhiều quá.",
    "Cho em một cốc cà phê sữa đá nha.",
]

# Northern word -> Southern word. Longer phrases come first so "bố mẹ" wins over "bố".
SOUTHERN = [
    ("bố mẹ", "ba má"),
    ("bố", "ba"),
    ("mẹ", "má"),
    ("quả", "trái"),
    ("cân", "ký"),
    ("thìa", "muỗng"),
    ("bát", "chén"),
    ("lợn", "heo"),
    ("đắt", "mắc"),
    ("lạc", "đậu phộng"),
    ("cốc", "ly"),
]

GLOSSARY = {
    "deadline": "hạn chót",
    "budget": "ngân sách",
    "savings account": "tài khoản tiết kiệm",
    "interest rate": "lãi suất",
    "stress": "căng thẳng",
    "meeting": "cuộc họp",
}

_HOW_DO_YOU_SAY = re.compile(r"how do (?:you|i) say (.+?)[?.!]*$", re.IGNORECASE)


def _word(w: str) -> re.Pattern:
    return re.compile(rf"(?<!\w){re.escape(w)}(?!\w)", re.IGNORECASE)


class FakeEars:
    def __init__(self, *_, **__):
        self._samples = cycle(SAMPLE_HEARD)

    def transcribe(self, path: Path) -> tuple[str, float]:
        return next(self._samples), 0.0


class FakeBrain:
    def __init__(self, delay: float = 1.0, **_):
        self.model = "fake"
        self.delay = delay

    def warm(self) -> float:
        return 0.0

    def respond(self, messages: list[dict]) -> BrainReply:
        start = time.perf_counter()
        time.sleep(self.delay)
        system = messages[0]["content"]
        name = re.search(r"^You are (.+?), ", system).group(1)
        you = re.search(r'call Austin "(\w+)"', system).group(1)
        said = messages[-1]["content"]

        if said.startswith("(Start the conversation"):
            reply = f"Chào {you} nha! {name} nè. Dạo này {you} sao rồi?"
            return BrainReply(reply, seconds=time.perf_counter() - start)

        asked = _HOW_DO_YOU_SAY.search(said)
        if asked:
            english = asked.group(1).strip().lower()
            word = GLOSSARY.get(english, f"({english})")
            reply = f"Cái đó mình nói là “{word}” đó {you}. {you.capitalize()} thử nói lại coi?"
            return BrainReply(reply, new_words=[{"word": word, "meaning_en": english}], seconds=time.perf_counter() - start)

        fixed, corrections = said, []
        for northern, southern in SOUTHERN:
            if _word(northern).search(fixed):
                fixed = _word(northern).sub(southern, fixed)
                corrections.append(
                    {
                        "said": northern,
                        "better": southern,
                        "why_en": f"In the South people say “{southern}”, not “{northern}”.",
                        "why_vi": f"Người miền Nam nói “{southern}”, không nói “{northern}”.",
                    }
                )
        echo = fixed.rstrip(".!?") if corrections else "Vậy hả"
        reply = f"{echo}. Rồi sao nữa {you}?"
        return BrainReply(reply, corrections=corrections, seconds=time.perf_counter() - start)


class FakeVoice:
    RATE = 16_000

    def __init__(self, *_, **__):
        pass

    def has_voice(self, name: str) -> bool:
        return True

    def speak(self, text: str, voice: str, out_path: Path) -> float:
        """Writes one soft beep per word (at most 12), so playback can be heard and timed."""
        start = time.perf_counter()
        samples = array.array("h")
        beep, gap = int(0.09 * self.RATE), int(0.06 * self.RATE)
        for i in range(min(len(text.split()), 12)):
            freq = 520 + 60 * (i % 4)
            for n in range(beep):
                envelope = math.sin(math.pi * n / beep)
                samples.append(int(6000 * envelope * math.sin(2 * math.pi * freq * n / self.RATE)))
            samples.extend([0] * gap)
        with wave.open(str(out_path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.RATE)
            w.writeframes(samples.tobytes())
        return time.perf_counter() - start

    def close(self) -> None:
        pass
