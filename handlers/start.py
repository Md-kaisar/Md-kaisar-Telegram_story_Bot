"""
/start, /help, /style, /language and other simple commands that don't need a photo.
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

import config
from database import db
from utils.keyboards import style_keyboard, language_keyboard

logger = logging.getLogger(__name__)

WELCOME = (
    "🌿 *Welcome to MuseBot*\n\n"
    "I'm a quiet poet who finds words in forests, rivers, sunsets, and rain\\.\n\n"
    "Send me a *nature photo* and I'll turn it into a poem, captions, a haiku, "
    "a short story, a color palette, and more\\.\n\n"
    "Or just explore with these commands:\n"
    "/poem /caption /quote /haiku /story /palette /prompt /mood \\— all work on your last photo\n"
    "/style \\— choose a writing style\n"
    "/language \\— choose a language\n"
    "/history \\— view past creations\n"
    "/favorite \\— save your last creation\n"
    "/share \\— get a shareable version of your last creation\n"
    "/stats \\— see your MuseBot journey\n\n"
    "🍃 Ready when you are\\."
)

HELP = (
    "🌸 *MuseBot Commands*\n\n"
    "*Send a photo* to unlock all creative actions for it, or use these directly on "
    "your most recently sent photo:\n"
    "/poem \\- original poem\n"
    "/caption \\- 5 Instagram captions\n"
    "/quote \\- one original quote\n"
    "/haiku \\- 5\\-7\\-5 haiku\n"
    "/story \\- short story\n"
    "/palette \\- color palette \\+ meanings\n"
    "/prompt \\- 3 writing prompts\n"
    "/mood \\- dominant mood detection\n\n"
    "*Preferences*\n"
    "/style \\- choose your poem style\n"
    "/language \\- choose your output language\n\n"
    "*Your journey*\n"
    "/history \\- recent creations\n"
    "/favorite \\- save your last creation\n"
    "/share \\- shareable version of your last creation\n"
    "/stats \\- your creative stats"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_new_user = db.upsert_user(user.id, user.username)
    await update.message.reply_text(WELCOME, parse_mode="MarkdownV2")

    if is_new_user and config.ADMIN_CHAT_ID:
        who = f"@{user.username}" if user.username else (user.first_name or "unknown")
        try:
            await context.bot.send_message(
                chat_id=config.ADMIN_CHAT_ID,
                text=f"🌱 New MuseBot user: {who} (ID: {user.id})",
            )
        except Exception:
            # Never let a failed admin notification (e.g. bad/unset ADMIN_CHAT_ID)
            # break the actual user's /start experience.
            logger.exception("Failed to send new-user notification to admin")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, parse_mode="MarkdownV2")


async def style_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎨 Choose your preferred *poem style*:",
        parse_mode="MarkdownV2",
        reply_markup=style_keyboard(),
    )


async def language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 Choose your *output language*:",
        parse_mode="MarkdownV2",
        reply_markup=language_keyboard(),
    )
