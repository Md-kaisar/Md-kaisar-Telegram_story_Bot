"""
Core dispatcher: given an action kind + an image key, runs the right AI Service
call, formats the result, saves it to history, and replies to the user.
Shared by both inline-button callbacks and standalone slash commands (/poem, /haiku, ...).

Efficiency notes:
- Every Gemini/PIL call is blocking, so it's offloaded via asyncio.to_thread. Calling
  these directly inside an `async def` would freeze the bot's single event loop for
  every other user for the duration of each network call.
- "do all" runs its independent sub-generations concurrently (they only share the
  scene description, fetched once) instead of one-by-one, cutting wall-clock time
  roughly 5-7x for that action.
- Rate limiting reserves the true number of upcoming API calls atomically before
  any work starts, so a partially-limited batch never runs half its calls for free
  and never gets billed for calls it didn't make.
"""
import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

import config
from database import db
from services import ai_service
from services.palette_service import extract_hex_palette
from utils import formatting
from utils.image_cache import get as cache_get, set_scene
from utils.keyboards import genre_keyboard, poem_result_keyboard, generic_result_keyboard
from utils.ratelimit import check_and_bump_n

logger = logging.getLogger(__name__)

ALL_SUB_KINDS = ["poem", "caption", "quote", "haiku", "mood", "palette", "prompt"]
SCENE_FREE_KINDS = {"palette"}  # kinds that don't need a scene description


async def _get_scene(image_key: str) -> str:
    entry = cache_get(image_key)
    if entry["scene"]:
        return entry["scene"]
    scene = await asyncio.to_thread(ai_service.describe_scene, entry["image_bytes"], entry["mime_type"])
    set_scene(image_key, scene)
    return scene


def _action_cost(kind: str, image_key: str) -> int:
    """How many real Gemini calls this action will make, given current cache state."""
    entry = cache_get(image_key)
    scene_cached = bool(entry and entry.get("scene"))
    if kind == "all":
        needs_scene = any(k not in SCENE_FREE_KINDS for k in ALL_SUB_KINDS)
        return (0 if scene_cached or not needs_scene else 1) + len(ALL_SUB_KINDS)
    needs_scene = kind not in SCENE_FREE_KINDS
    return (0 if scene_cached or not needs_scene else 1) + 1


async def no_photo_message(update: Update):
    await update.effective_message.reply_text(
        "🌿 Please send me a nature photo first, then I can create this for you\\.",
        parse_mode="MarkdownV2",
    )


async def rate_limited_message(update: Update):
    await update.effective_message.reply_text(
        f"🍃 You've reached today's creative limit \\({config.DAILY_GENERATION_LIMIT} generations\\)\\. "
        "Please come back tomorrow — good things take a little patience\\.",
        parse_mode="MarkdownV2",
    )


# ---- Per-kind: compute (blocking work, off the event loop) ----

async def _compute(kind: str, scene: str, style: str, language: str, entry: dict):
    if kind == "poem":
        return await asyncio.to_thread(ai_service.generate_poem, scene, style, language)
    if kind == "caption":
        return await asyncio.to_thread(ai_service.generate_captions, scene, language)
    if kind == "quote":
        return await asyncio.to_thread(ai_service.generate_quote, scene, language)
    if kind == "haiku":
        return await asyncio.to_thread(ai_service.generate_haiku, scene, language)
    if kind == "mood":
        return await asyncio.to_thread(ai_service.generate_mood, scene)
    if kind == "prompt":
        return await asyncio.to_thread(ai_service.generate_prompts, scene, language)
    if kind == "palette":
        hex_colors = await asyncio.to_thread(extract_hex_palette, entry["image_bytes"], 5)
        return await asyncio.to_thread(ai_service.generate_palette_meanings, hex_colors)
    raise ValueError(f"_compute doesn't handle kind={kind}")


# ---- Per-kind: format, save to history, and send ----

async def _send_result(kind: str, data, msg, user_id: int, image_key: str, entry: dict):
    if kind == "poem":
        hid = db.add_history(user_id, "poem", data["title"], data["poem"],
                              mood=data.get("mood"), image_file_id=entry["file_id"])
        await msg.reply_text(formatting.format_poem(data), parse_mode="MarkdownV2",
                              reply_markup=poem_result_keyboard(hid, image_key))
    elif kind == "caption":
        content = "\n".join(f"{k}: {v}" for k, v in data.items())
        hid = db.add_history(user_id, "caption", "Instagram Captions", content,
                              image_file_id=entry["file_id"])
        await msg.reply_text(formatting.format_captions(data), parse_mode="MarkdownV2",
                              reply_markup=generic_result_keyboard(hid))
    elif kind == "quote":
        hid = db.add_history(user_id, "quote", "Quote", data, image_file_id=entry["file_id"])
        await msg.reply_text(formatting.format_quote(data), parse_mode="MarkdownV2",
                              reply_markup=generic_result_keyboard(hid))
    elif kind == "haiku":
        content = "\n".join([data["line1"], data["line2"], data["line3"]])
        hid = db.add_history(user_id, "haiku", "Haiku", content, image_file_id=entry["file_id"])
        await msg.reply_text(formatting.format_haiku(data), parse_mode="MarkdownV2",
                              reply_markup=generic_result_keyboard(hid))
    elif kind == "mood":
        db.add_history(user_id, "mood", "Mood", data["mood"], mood=data["mood"],
                        image_file_id=entry["file_id"])
        await msg.reply_text(formatting.format_mood(data), parse_mode="MarkdownV2")
    elif kind == "story":
        hid = db.add_history(user_id, "story", data["title"], data["story"],
                              image_file_id=entry["file_id"])
        await msg.reply_text(formatting.format_story(data), parse_mode="MarkdownV2",
                              reply_markup=generic_result_keyboard(hid))
    elif kind == "palette":
        content = "\n".join(f"{c.get('hex')} {c.get('name')} -> {c.get('emotion')}" for c in data)
        hid = db.add_history(user_id, "palette", "Color Palette", content,
                              image_file_id=entry["file_id"])
        await msg.reply_text(formatting.format_palette(data), parse_mode="MarkdownV2",
                              reply_markup=generic_result_keyboard(hid))
    elif kind == "prompt":
        content = "\n".join(data)
        hid = db.add_history(user_id, "prompt", "Writing Prompts", content,
                              image_file_id=entry["file_id"])
        await msg.reply_text(formatting.format_prompts(data), parse_mode="MarkdownV2",
                              reply_markup=generic_result_keyboard(hid))


async def run_action(update: Update, context: ContextTypes.DEFAULT_TYPE, kind: str,
                      image_key: str, genre: str | None = None, chat_message=None):
    """chat_message is the Message object to reply to (works for both commands and callbacks)."""
    user = update.effective_user
    msg = chat_message or update.effective_message

    entry = cache_get(image_key)
    if not entry:
        await no_photo_message(update)
        return

    # Story needs a genre first; showing the picker costs nothing, so skip rate limiting.
    if kind == "story" and not genre:
        await msg.reply_text("📖 Pick a genre for your story:", reply_markup=genre_keyboard(image_key))
        return

    cost = _action_cost(kind, image_key)
    allowed, _ = check_and_bump_n(user.id, cost)
    if not allowed:
        await rate_limited_message(update)
        return

    user_row = db.get_user(user.id)
    language = user_row["language"] if user_row else "en"
    style = user_row["style"] if user_row else "Nature"

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        if kind == "all":
            scene = await _get_scene(image_key)
            # Independent sub-generations only depend on the (already fetched) scene,
            # so run them concurrently instead of one Gemini round-trip at a time.
            tasks = [_compute(k, scene, style, language, entry) for k in ALL_SUB_KINDS]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for sub_kind, result in zip(ALL_SUB_KINDS, results):
                if isinstance(result, Exception):
                    logger.error("Sub-generation '%s' failed in 'all' batch: %s", sub_kind, result)
                    await msg.reply_text(
                        f"🌧️ Couldn't create the {formatting.esc(sub_kind)} this time\\.",
                        parse_mode="MarkdownV2",
                    )
                    continue
                await _send_result(sub_kind, result, msg, user.id, image_key, entry)
            await msg.reply_text("📖 Want a story too? Tap a genre:", reply_markup=genre_keyboard(image_key))
            return

        if kind == "story":
            scene = await _get_scene(image_key)
            data = await asyncio.to_thread(ai_service.generate_story, scene, genre, language)
            await _send_result("story", data, msg, user.id, image_key, entry)
            return

        scene = None if kind in SCENE_FREE_KINDS else await _get_scene(image_key)
        data = await _compute(kind, scene, style, language, entry)
        await _send_result(kind, data, msg, user.id, image_key, entry)

    except ai_service.AIError as e:
        await msg.reply_text(
            "🌧️ Something clouded my thoughts just now\\. Please try again in a moment\\.",
            parse_mode="MarkdownV2",
        )
        logger.error("AIError during action %s: %s", kind, e)
