"""
/history, /favorite, /share, /stats — commands about the user's past creations.
"""
from telegram import Update
from telegram.ext import ContextTypes

from database import db
from utils import formatting
from utils.keyboards import generic_result_keyboard


async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    rows = db.get_history(user.id, limit=10)
    if not rows:
        await update.message.reply_text(
            "🌱 No creations yet\\. Send me a nature photo to begin\\.", parse_mode="MarkdownV2"
        )
        return
    await update.message.reply_text("🗂 *Your recent creations:*", parse_mode="MarkdownV2")
    for row in rows:
        await update.message.reply_text(
            formatting.format_history_item(row),
            parse_mode="MarkdownV2",
            reply_markup=generic_result_keyboard(row["id"]),
        )


async def favorite_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    rows = db.get_history(user.id, limit=1)
    if not rows:
        await update.message.reply_text(
            "🌱 You don't have a creation yet to save\\. Send a photo first\\.",
            parse_mode="MarkdownV2",
        )
        return
    latest = rows[0]
    added = db.add_favorite(user.id, latest["id"])
    text = "⭐ Saved your latest creation to favorites\\!" if added else "⭐ That's already a favorite\\."
    await update.message.reply_text(text, parse_mode="MarkdownV2")


async def share_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    rows = db.get_history(user.id, limit=1)
    if not rows:
        await update.message.reply_text(
            "🌱 Nothing to share yet\\. Send a photo and create something first\\.",
            parse_mode="MarkdownV2",
        )
        return
    await update.message.reply_text(formatting.format_share(rows[0]), parse_mode="MarkdownV2")


async def favorites_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    rows = db.get_favorites(user.id, limit=10)
    if not rows:
        await update.message.reply_text(
            "⭐ No favorites saved yet\\. Use /favorite after a creation you love\\.",
            parse_mode="MarkdownV2",
        )
        return
    await update.message.reply_text("⭐ *Your favorites:*", parse_mode="MarkdownV2")
    for row in rows:
        await update.message.reply_text(formatting.format_history_item(row), parse_mode="MarkdownV2")


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    stats = db.get_stats(user.id)
    kind_lines = "\n".join(
        f"  • {formatting.esc(k)}: {v}" for k, v in stats["by_kind"].items()
    ) or "  • None yet"
    top_mood = formatting.esc(stats["top_mood"]) if stats["top_mood"] else "—"
    text = (
        f"📊 *Your MuseBot Journey*\n\n"
        f"Total creations: *{stats['total']}*\n"
        f"By type:\n{kind_lines}\n\n"
        f"Most frequent mood: *{top_mood}*\n"
        f"Favorites saved: *{stats['favorites']}*"
    )
    await update.message.reply_text(text, parse_mode="MarkdownV2")
