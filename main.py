"""
MuseBot entry point.
Run with: python main.py
Requires TELEGRAM_BOT_TOKEN and GEMINI_API_KEY set (see .env.example).
"""
import logging
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import TELEGRAM_BOT_TOKEN
from database.db import init_db
from handlers import start, photo, callbacks, history

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("musebot")


# ============================================
# Render port-scan health check
# ============================================
# MuseBot only talks to Telegram via polling and never opens an HTTP port on
# its own. Render's Web Service type expects something listening on $PORT,
# otherwise it logs "No open ports detected" and can eventually treat the
# service as unhealthy. This tiny server runs on a background thread purely
# to satisfy that port scan -- it has nothing to do with bot functionality.
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class _HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"MuseBot is running")

    def log_message(self, format, *args):
        pass  # silence default request logging, keep our own logs clean


def _start_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), _HealthCheckHandler)
    server.serve_forever()


threading.Thread(target=_start_health_check_server, daemon=True).start()
# ============================================
# End health check
# ============================================


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Unhandled exception while processing update: %s", update, exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "🌧️ Something unexpected happened. Please try again in a moment."
            )
        except Exception:
            pass


def build_app() -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Add it to your .env file.")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Core commands
    app.add_handler(CommandHandler("start", start.start))
    app.add_handler(CommandHandler("help", start.help_cmd))
    app.add_handler(CommandHandler("style", start.style_cmd))
    app.add_handler(CommandHandler("language", start.language_cmd))

    # Standalone creative commands (act on the last sent photo)
    app.add_handler(CommandHandler("poem", photo.poem_cmd))
    app.add_handler(CommandHandler("caption", photo.caption_cmd))
    app.add_handler(CommandHandler("quote", photo.quote_cmd))
    app.add_handler(CommandHandler("haiku", photo.haiku_cmd))
    app.add_handler(CommandHandler("story", photo.story_cmd))
    app.add_handler(CommandHandler("palette", photo.palette_cmd))
    app.add_handler(CommandHandler("prompt", photo.prompt_cmd))
    app.add_handler(CommandHandler("mood", photo.mood_cmd))

    # History / favorites / sharing / stats
    app.add_handler(CommandHandler("history", history.history_cmd))
    app.add_handler(CommandHandler("favorite", history.favorite_cmd))
    app.add_handler(CommandHandler("favorites", history.favorites_list_cmd))
    app.add_handler(CommandHandler("share", history.share_cmd))
    app.add_handler(CommandHandler("stats", history.stats_cmd))

    # Photos + inline button callbacks
    app.add_handler(MessageHandler(filters.PHOTO, photo.handle_photo))
    app.add_handler(CallbackQueryHandler(callbacks.handle_callback))

    app.add_error_handler(on_error)
    return app


import asyncio
# Python 3.14 removed asyncio.get_event_loop()'s auto-create behavior in the main
# thread. python-telegram-bot's run_polling() still calls get_event_loop()
# internally, so we pre-create and set one here to avoid a RuntimeError,
# regardless of which Python version the host ends up using.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())


def main():
    init_db()
    app = build_app()
    logger.info("MuseBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
