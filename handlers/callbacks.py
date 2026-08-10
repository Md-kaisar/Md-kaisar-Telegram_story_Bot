"""
Routes every inline-button press. Callback data is kept short (Telegram's 64-byte
limit) using colon-delimited tokens: "act:poem:<key>", "genre:Fantasy:<key>",
"fav:<history_id>", "share:<history_id>", "style:<Style>", "lang:<code>".
"""
from telegram import Update
from telegram.ext import ContextTypes

from database import db
from handlers.actions import run_action
from utils import formatting

STYLE_CONFIRM = "🎨 Style set to *{style}*\\. Send a photo whenever you're ready\\."
LANG_CONFIRM = "🌍 Language updated\\. I'll write in *{lang}* from now on\\."

from config import LANGUAGES


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    parts = data.split(":")
    action = parts[0]
    user = update.effective_user

    if action == "act":
        kind, image_key = parts[1], parts[2]
        await run_action(update, context, kind, image_key, chat_message=query.message)

    elif action == "genre":
        genre, image_key = parts[1], parts[2]
        await run_action(update, context, "story", image_key, genre=genre, chat_message=query.message)

    elif action == "style":
        style = parts[1]
        db.set_style(user.id, style)
        await query.message.reply_text(
            STYLE_CONFIRM.format(style=formatting.esc(style)), parse_mode="MarkdownV2"
        )

    elif action == "lang":
        code = parts[1]
        db.set_language(user.id, code)
        lang_name = formatting.esc(LANGUAGES.get(code, code))
        await query.message.reply_text(LANG_CONFIRM.format(lang=lang_name), parse_mode="MarkdownV2")

    elif action == "fav":
        history_id = int(parts[1])
        added = db.add_favorite(user.id, history_id)
        text = "⭐ Saved to your favorites\\!" if added else "⭐ Already in your favorites\\."
        await query.message.reply_text(text, parse_mode="MarkdownV2")

    elif action == "share":
        history_id = int(parts[1])
        row = db.get_history_item(history_id)
        if row:
            await query.message.reply_text(formatting.format_share(row), parse_mode="MarkdownV2")
