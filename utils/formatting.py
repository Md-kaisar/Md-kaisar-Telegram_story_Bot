"""
Formatting helpers that turn AI service outputs into calm, tasteful Telegram messages.
Uses MarkdownV2-safe escaping so titles/content with special characters don't break rendering.
"""
import re

_MDV2_SPECIAL = r"_*[]()~`>#+-=|{}.!"


def esc(text: str) -> str:
    """Escape text for Telegram MarkdownV2."""
    if text is None:
        return ""
    return re.sub(f"([{re.escape(_MDV2_SPECIAL)}])", r"\\\1", str(text))


def format_poem(data: dict) -> str:
    title = esc(data["title"])
    poem = esc(data["poem"])
    mood = esc(data.get("mood", ""))
    reflection = esc(data.get("reflection", ""))
    return (
        f"🌿 *{title}*\n\n"
        f"{poem}\n\n"
        f"_Mood: {mood}_\n"
        f"💭 _{reflection}_"
    )


def format_captions(data: dict) -> str:
    lines = ["📸 *Instagram Captions*\n"]
    labels = {
        "poetic": "Poetic",
        "aesthetic": "Aesthetic",
        "short": "Short",
        "minimalist": "Minimalist",
        "deep": "Deep",
    }
    for key, label in labels.items():
        val = data.get(key, "")
        if val:
            lines.append(f"• _{esc(label)}:_ {esc(val)}")
    return "\n".join(lines)


def format_quote(quote: str) -> str:
    return f"💬 _{esc(quote)}_"


def format_haiku(data: dict) -> str:
    return (
        f"🍃 *Haiku*\n\n"
        f"{esc(data['line1'])}\n"
        f"{esc(data['line2'])}\n"
        f"{esc(data['line3'])}"
    )


def format_mood(data: dict) -> str:
    mood = esc(data["mood"].capitalize())
    confidence = data.get("confidence", 70)
    bar_len = round(confidence / 10)
    bar = "▓" * bar_len + "░" * (10 - bar_len)
    return f"🎭 *Mood:* {mood}\n`{bar}` {confidence}%"


def format_story(data: dict) -> str:
    return f"📖 *{esc(data['title'])}*\n\n{esc(data['story'])}"


def format_prompts(prompt_list: list) -> str:
    lines = ["✍️ *Writing Prompts*\n"]
    for i, p in enumerate(prompt_list, 1):
        lines.append(f"{i}\\. _{esc(p)}_")
    return "\n".join(lines)


def format_palette(colors: list) -> str:
    lines = ["🎨 *Color Palette*\n"]
    for c in colors:
        hexv = esc(c.get("hex", ""))
        name = esc(c.get("name", ""))
        emotion = esc(c.get("emotion", ""))
        lines.append(f"`{hexv}` — *{name}* → {emotion}")
    return "\n".join(lines)


def format_history_item(row) -> str:
    kind = esc(row["kind"].capitalize())
    title = esc(row["title"] or "")
    snippet = (row["content"] or "")[:120].replace("\n", " ")
    snippet = esc(snippet)
    return f"🗂 *{kind}* — {title}\n{snippet}…"


def format_share(row) -> str:
    """A polished, shareable version of any saved creation."""
    title = esc(row["title"] or "MuseBot Creation")
    content = esc(row["content"] or "")
    mood = esc(row["mood"] or "")
    footer = "\n\n✨ _Created with MuseBot_"
    mood_line = f"\n\n_Mood: {mood}_" if mood else ""
    return f"🌸 *{title}*\n\n{content}{mood_line}{footer}"
