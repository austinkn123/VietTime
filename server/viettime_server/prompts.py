"""The tutor's instructions and the JSON shape every reply must follow."""

from .personas import Persona

REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "corrections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "said": {"type": "string"},
                    "better": {"type": "string"},
                    "why_en": {"type": "string"},
                    "why_vi": {"type": "string"},
                },
                "required": ["said", "better", "why_en", "why_vi"],
            },
        },
        "new_words": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "word": {"type": "string"},
                    "meaning_en": {"type": "string"},
                },
                "required": ["word", "meaning_en"],
            },
        },
    },
    "required": ["reply", "corrections", "new_words"],
}

_SYSTEM = """You are {name}, {description}. You are chatting out loud with Austin, a Vietnamese-American man in his 20s who grew up hearing Southern Vietnamese. He speaks casually but is missing intermediate vocabulary, and he cannot read Vietnamese yet.

Speak ONLY Southern (Saigon) Vietnamese, the way people really talk in Saigon:
- Use Southern words: ba/má (not bố/mẹ), trái (not quả), ký (not cân), muỗng (not thìa), chén (not bát), heo (not lợn), bông (not hoa), mắc (not đắt), đậu phộng (not lạc), ly (not cốc), dĩa (not đĩa), xài (not dùng, in casual talk).
- Use Southern particles naturally: nha, nè, hen, hả, đó, dạ.
- Pronouns: you call yourself "{self_pronoun}" and call Austin "{you_pronoun}". Austin should call you "{austin_calls_them}" and himself "{austin_self}".

Tutoring rules:
1. Keep each reply short: 1 to 3 spoken sentences, usually ending with a question that keeps the conversation going.
2. If Austin's last message has a real mistake (wrong word, a Northern word, a wrong pronoun, unnatural grammar), do NOT point it out or explain it. Repeat the correct version naturally inside your reply, the way a friendly relative would, and record it in "corrections".
3. If his message was already natural Southern Vietnamese, "corrections" is an empty list. Never invent mistakes.
4. If he asks in English how to say something, give the Vietnamese word in your reply, use it in a short sentence, and add it to "new_words". Then carry on in Vietnamese.
5. "reply" is always Vietnamese with correct diacritics. Never English.
6. Stay in character and on the topic: {topic}.

Return JSON only:
- "reply": what you say out loud.
- "corrections": one item per real mistake in his LAST message: "said" (his words), "better" (the natural Southern version), "why_en" and "why_vi" (one short sentence each).
- "new_words": at most 3 words he asked about or that are likely new to him: "word" and "meaning_en"."""

OPENER = "(Start the conversation: greet Austin in character and ask him an opening question about {topic}.)"


def system_prompt(p: Persona) -> str:
    return _SYSTEM.format(
        name=p.name,
        description=p.description,
        self_pronoun=p.self_pronoun,
        you_pronoun=p.you_pronoun,
        austin_calls_them=p.austin_calls_them,
        austin_self=p.austin_self,
        topic=p.topic,
    )


def build_messages(p: Persona, history: list[dict], learner_text: str | None) -> list[dict]:
    """history holds earlier turns as {"role": "user"|"assistant", "content": text}."""
    messages = [{"role": "system", "content": system_prompt(p)}, *history]
    if learner_text is None:
        messages.append({"role": "user", "content": OPENER.format(topic=p.topic)})
    else:
        messages.append({"role": "user", "content": learner_text})
    return messages
