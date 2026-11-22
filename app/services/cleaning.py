# app/services/cleaning.py
"""Clean extracted text without changing what it says."""
import re
import unicodedata

# Characters you can't see that still change the text: zero-width spaces, direction marks, byte-order mark
INVISIBLE = re.compile("[\u00ad\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]")
# Control characters (like the zero byte some PDF readers leave behind), except new line and tab
CONTROL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
TATWEEL = "\u0640"  # the Arabic stretching line: كـــشف means the same as كشف
ARABIC_WORD = re.compile(r"[\u0600-\u06ff]+")


def clean_text(text: str) -> str:
    # 1. One standard form for every character. Arabic "presentation forms" (ﻛﺸﻒ) become normal letters (كشف)
    text = unicodedata.normalize("NFKC", text)
    # 2. Remove what nobody can see, and the decorative tatweel
    text = CONTROL.sub("", INVISIBLE.sub("", text)).replace(TATWEEL, "")
    # 3. Tidy spaces and empty lines, but keep paragraph breaks: the chunker uses them
    text = text.replace("\r\n", "\n").replace("\t", " ").replace("\u00a0", " ")
    lines = [re.sub(r" {2,}", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def looks_broken(text: str) -> bool:
    """Arabic words split into single letters ("ال خ دما ت") mean the PDF text came out broken."""
    words = ARABIC_WORD.findall(text)
    if len(words) < 20:
        return False
    single_letters = sum(1 for word in words if len(word) == 1)
    return single_letters / len(words) > 0.2
