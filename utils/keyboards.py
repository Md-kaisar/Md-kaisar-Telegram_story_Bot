"""
Reusable inline keyboards.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import LANGUAGES, STYLES, STORY_GENRES


def main_action_keyboard(image_key: str) -> InlineKeyboardMarkup:
    """Shown after a photo is uploaded, so the user can pick what to create from it."""
    rows = [
        [
            InlineKeyboardButton("🌿 Poem", callback_data=f"act:poem:{image_key}"),
            InlineKeyboardButton("📸 Captions", callback_data=f"act:caption:{image_key}"),
        ],
        [
            InlineKeyboardButton("💬 Quote", callback_data=f"act:quote:{image_key}"),
            InlineKeyboardButton("🍃 Haiku", callback_data=f"act:haiku:{image_key}"),
        ],
        [
            InlineKeyboardButton("🎭 Mood", callback_data=f"act:mood:{image_key}"),
            InlineKeyboardButton("📖 Story", callback_data=f"act:story:{image_key}"),
        ],
        [
            InlineKeyboardButton("🎨 Palette", callback_data=f"act:palette:{image_key}"),
            InlineKeyboardButton("✍️ Prompts", callback_data=f"act:prompt:{image_key}"),
        ],
        [InlineKeyboardButton("🌸 Do all of the above", callback_data=f"act:all:{image_key}")],
    ]
    return InlineKeyboardMarkup(rows)


def style_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, style in enumerate(STYLES, 1):
        row.append(InlineKeyboardButton(style, callback_data=f"style:{style}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def language_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(name, callback_data=f"lang:{code}")]
            for code, name in LANGUAGES.items()]
    return InlineKeyboardMarkup(rows)


def genre_keyboard(image_key: str) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, genre in enumerate(STORY_GENRES, 1):
        row.append(InlineKeyboardButton(genre, callback_data=f"genre:{genre}:{image_key}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def poem_result_keyboard(history_id: int, image_key: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("⭐ Save Favorite", callback_data=f"fav:{history_id}"),
            InlineKeyboardButton("🔄 Regenerate", callback_data=f"act:poem:{image_key}"),
        ],
        [InlineKeyboardButton("📤 Share Version", callback_data=f"share:{history_id}")],
    ]
    return InlineKeyboardMarkup(rows)


def generic_result_keyboard(history_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("⭐ Save Favorite", callback_data=f"fav:{history_id}"),
            InlineKeyboardButton("📤 Share Version", callback_data=f"share:{history_id}"),
        ],
    ]
    return InlineKeyboardMarkup(rows)
