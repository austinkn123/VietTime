"""Tutor personas, one per topic, with the Southern pronouns each side uses.

Mirrors the "Personas" table in the plan doc. Every voice is a Southern
(region "Nam") preset of VieNeu-TTS v3 Turbo.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    key: str
    topic: str
    name: str
    description: str
    self_pronoun: str  # what the tutor calls themselves
    you_pronoun: str  # what the tutor calls Austin
    austin_calls_them: str
    austin_self: str
    voice: str  # VieNeu preset voice name


PERSONAS = {
    p.key: p
    for p in [
        Persona(
            key="family",
            topic="family and elders",
            name="Cô Tư",
            description="Austin's aunt who lives in Saigon",
            self_pronoun="cô",
            you_pronoun="con",
            austin_calls_them="cô",
            austin_self="con",
            voice="Kim Thanh",
        ),
        Persona(
            key="food",
            topic="food and the market",
            name="Chị Ba",
            description="a fruit vendor at Chợ Bến Thành",
            self_pronoun="chị",
            you_pronoun="em",
            austin_calls_them="chị",
            austin_self="em",
            voice="Thục Đoan",
        ),
        Persona(
            key="work",
            topic="work and tech",
            name="Anh Khoa",
            description="a software engineer in Saigon, a few years older than Austin",
            self_pronoun="anh",
            you_pronoun="em",
            austin_calls_them="anh",
            austin_self="em",
            voice="Adam",
        ),
        Persona(
            key="news",
            topic="news and current events",
            name="Chú Sáu",
            description="a retired uncle who follows the news closely",
            self_pronoun="chú",
            you_pronoun="con",
            austin_calls_them="chú",
            austin_self="con",
            voice="Đức Trí",
        ),
        Persona(
            key="feelings",
            topic="feelings and opinions",
            name="Vy",
            description="a close friend the same age as Austin",
            self_pronoun="tui",
            you_pronoun="ông",
            austin_calls_them="bà",
            austin_self="tui",
            voice="Mỹ Duyên",
        ),
        Persona(
            key="errands",
            topic="errands like the doctor, the bank or a phone plan",
            name="Ngân",
            description="a bank teller a little younger than Austin",
            self_pronoun="em",
            you_pronoun="anh",
            austin_calls_them="em",
            austin_self="anh",
            voice="Thùy Dung",
        ),
    ]
}
