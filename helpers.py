import random

_STYLE = {"a": "ᴧ", "e": "є", "o": "σ", "n": "η", "u": "υ"}

_SMALLCAPS = {
    "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ", "f": "ғ", "g": "ɢ",
    "h": "ʜ", "i": "ɪ", "j": "ᴊ", "k": "ᴋ", "l": "ʟ", "m": "ᴍ", "n": "ɴ",
    "o": "ᴏ", "p": "ᴘ", "q": "ǫ", "r": "ʀ", "s": "s", "t": "ᴛ", "u": "ᴜ",
    "v": "ᴠ", "w": "ᴡ", "x": "x", "y": "ʏ", "z": "ᴢ",
}

PROCESSING_EMOJIS = ["🧪", "🦋", "🔍", "⚡", "✨"]

DIVIDER = "•── ⋅ ⋅  ────── ⋅᯽⋅ ────── ⋅ ⋅ ⋅──•"
CREDIT_LINE = "⚡ **Pᴏᴡᴇʀ ʙʏ Zᴀsɪᴍ • Cʀᴇᴅɪᴛ [NSG CHEATS](https://t.me/NSG_CHEATS)**"


def smallcaps(text: str) -> str:
    return "".join(
        _STYLE.get(ch.lower()) or _SMALLCAPS.get(ch.lower(), ch) if ch.isalpha() else ch
        for ch in text
    )


def smallcaps_title(text: str) -> str:
    out = []
    new_word = True
    for ch in text:
        if ch.isalpha():
            out.append(
                ch.upper()
                if new_word
                else (_STYLE.get(ch.lower()) or _SMALLCAPS.get(ch.lower(), ch))
            )
            new_word = False
        else:
            out.append(ch)
            new_word = ch in " -_/\n"
    return "".join(out)


def fancy_italic(text: str) -> str:
    out = []
    for ch in text:
        if "A" <= ch <= "Z":
            out.append(chr(0x1D63C + (ord(ch) - ord("A"))))
        elif "a" <= ch <= "z":
            out.append(chr(0x1D656 + (ord(ch) - ord("a"))))
        else:
            out.append(ch)
    return "".join(out)


def random_processing_text() -> str:
    return f"{random.choice(PROCESSING_EMOJIS)} {smallcaps_title('processing request')}..."


def format_duration(seconds) -> str:
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return str(seconds) if seconds else "04:00"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def duration_to_seconds(duration_str: str) -> int:
    if not duration_str:
        return 240
    parts = str(duration_str).split(":")
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        return 240
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def format_uptime(seconds) -> str:
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        seconds = 0
    h, rem = divmod(max(seconds, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{h}ʜ:{m}ᴍ:{s}s"


def expandable_quote(text: str) -> str:
    return f"<blockquote expandable>{text}</blockquote>"


def quote(text: str) -> str:
    return f"<blockquote>{text}</blockquote>"


def strip_quotes(text: str) -> str:
    return (
        text.replace("<blockquote expandable>", "")
        .replace("<blockquote>", "")
        .replace("</blockquote>", "")
    )


def bullet_lines(items) -> str:
    return "\n".join(f"╰┈➤ {i}" for i in items if i)