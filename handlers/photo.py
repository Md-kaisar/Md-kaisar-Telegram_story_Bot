"""
Handles incoming photos (downloads + caches them, shows the action menu) and the
standalone slash commands (/poem, /caption, /quote, /haiku, /story, /palette,
/prompt, /mood) which operate on the user's most recently sent photo.
"""
from telegram import Update
from telegram.ext import ContextTypes

from database import db
from handlers.actions import run_action, no_photo_message
from utils.image_cache import new_key, put
from utils.keyboards import main_action_keyboard


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username)

    photo = update.message.photo[-1]  # highest resolution
    tg_file = await photo.get_file()
    image_bytes = bytes(await tg_file.download_as_bytearray())

    key = new_key()
    put(key, image_bytes=image_bytes, file_id=photo.file_id)
    context.user_data["last_image_key"] = key

    await update.message.reply_text(
        "🌿 A lovely scene\\. What shall I create from it?",
        parse_mode="MarkdownV2",
        reply_markup=main_action_keyboard(key),
    )


async def _standalone(update: Update, context: ContextTypes.DEFAULT_TYPE, kind: str):
    image_key = context.user_data.get("last_image_key")
    if not image_key:
        await no_photo_message(update)
        return
    await run_action(update, context, kind, image_key)


async def poem_cmd(update, context):
    await _standalone(update, context, "poem")


async def caption_cmd(update, context):
    await _standalone(update, context, "caption")


async def quote_cmd(update, context):
    await _standalone(update, context, "quote")


async def haiku_cmd(update, context):
    await _standalone(update, context, "haiku")


async def story_cmd(update, context):
    await _standalone(update, context, "story")


async def palette_cmd(update, context):
    await _standalone(update, context, "palette")


async def prompt_cmd(update, context):
    await _standalone(update, context, "prompt")


async def mood_cmd(update, context):
    await _standalone(update, context, "mood")
