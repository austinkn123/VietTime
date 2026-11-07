"""Test material for Step 0.

SCRIPTED: typed learner turns with the kinds of mistakes a Southern heritage
speaker makes (Northern words, wrong pronouns, English mixed in). These test the
brain and voice without needing a microphone.

RECORDING_PROMPTS: English instructions Austin follows out loud, so the ears are
tested on his real voice, including English words mixed into Vietnamese.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scripted:
    key: str
    persona: str
    turns: tuple[str, ...]
    expect: str  # what a good tutor should fix, for the reviewer


SCRIPTED = [
    Scripted(
        "family-parents",
        "family",
        (
            "Dạ con khỏe. Hôm qua con đi ăn với bố mẹ ở nhà hàng.",
            "Con muốn học nấu canh chua nhưng con không biết bắt đầu làm sao.",
        ),
        "bố mẹ -> ba má",
    ),
    Scripted(
        "family-pronoun",
        "family",
        (
            "Cô ơi, tôi nhớ cô lắm.",
            "Tết này tôi sẽ về Việt Nam thăm cả nhà.",
        ),
        "tôi -> con when talking to an aunt",
    ),
    Scripted(
        "market-weight",
        "food",
        (
            "Chị ơi, cho em hai cân xoài.",
            "Cái này bao nhiêu tiền một quả?",
        ),
        "cân -> ký, quả -> trái",
    ),
    Scripted(
        "market-english",
        "food",
        (
            "Em muốn mua một cái... how do you say spoon?",
            "Em cũng cần mua một cái bát nữa.",
        ),
        "spoon = muỗng (new word), bát -> chén",
    ),
    Scripted(
        "work-busy",
        "work",
        (
            "Em làm software engineer, em viết code cho một công ty ở Houston.",
            "Công việc của em là rất bận, nhưng em thích nó.",
        ),
        "'là rất bận' -> 'bận lắm'; first turn is fine",
    ),
    Scripted(
        "work-deadline",
        "work",
        (
            "Tuần này em có nhiều meeting quá, em không có thời gian làm việc thật.",
            "Làm sao nói deadline bằng tiếng Việt hả anh?",
        ),
        "deadline = hạn chót (new word)",
    ),
    Scripted(
        "news-housing",
        "news",
        (
            "Chú ơi, con đọc tin tức là giá nhà ở Texas tăng nhiều lắm.",
            "Con mua nhà năm ngoái, tiền lãi... how do you say interest rate?",
        ),
        "'đọc tin tức là' -> 'đọc tin thấy'; interest rate = lãi suất (new word)",
    ),
    Scripted(
        "feelings-stress",
        "feelings",
        (
            "Bà ơi, dạo này tui hơi buồn vì công việc stress quá.",
            "Tui cảm thấy là tui không có tiến bộ trong tiếng Việt.",
        ),
        "'không có tiến bộ' -> 'không tiến bộ gì hết'; first turn is natural",
    ),
    Scripted(
        "bank-account",
        "errands",
        (
            "Chào em, anh muốn mở một tài khoản tiết kiệm.",
            "Anh cần mang cái gì? Anh có cái ID với cái passport.",
        ),
        "ID -> căn cước / giấy tờ tùy thân, passport -> hộ chiếu",
    ),
    Scripted(
        "bank-card",
        "errands",
        (
            "Em ơi, anh bị mất cái thẻ ngân hàng hôm qua.",
            "Anh muốn làm cái mới thì mất bao lâu?",
        ),
        "both turns are natural; it should not invent corrections",
    ),
]


@dataclass(frozen=True)
class RecordingPrompt:
    key: str
    persona: str
    say: str


RECORDING_PROMPTS = [
    RecordingPrompt("aunt-food", "family", "Greet Cô Tư (your aunt) and tell her what you ate today."),
    RecordingPrompt("market-mango", "food", "Tell Chị Ba at the market you want 2 kilos of mangoes and ask the price."),
    RecordingPrompt(
        "work-job",
        "work",
        "Explain your job to Anh Khoa. Use the English words 'software' and 'meeting' in your sentence.",
    ),
    RecordingPrompt("news-houses", "news", "Ask Chú Sáu what he thinks about house prices in Texas."),
    RecordingPrompt("feelings-week", "feelings", "Tell Vy how you've been feeling this week."),
    RecordingPrompt(
        "bank-savings",
        "errands",
        "Ask Ngân at the bank how to open a savings account. Say 'savings' in English if you don't know the word.",
    ),
    RecordingPrompt(
        "ask-budget",
        "work",
        "Start a sentence in Vietnamese, then ask in English: 'how do you say budget?'",
    ),
    RecordingPrompt("free-talk", "feelings", "Say anything you like for 10 to 15 seconds."),
]
