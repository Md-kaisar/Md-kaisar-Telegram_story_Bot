"""
MuseBot entry point.
Run with: python main.py
Requires TELEGRAM_BOT_TOKEN and GEMINI_API_KEY set (see .env.example).
"""
import logging
from telegram import Update
from telegram.error import Conflict
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
    try:
        server = HTTPServer(("0.0.0.0", port), _HealthCheckHandler)
    except OSError:
        # If this ever fails to bind (e.g. a stale process still holding the port during
        # a Render restart), log it loudly instead of letting the daemon thread die
        # silently -- a silent failure here would look like "no open ports detected" on
        # Render with no clue why, which is worse than an explicit log line.
        logger.exception("Health check server failed to bind to port %s", port)
        return
    server.serve_forever()


# Under normal execution (`python main.py`), Python's own module-caching guarantees this
# top-level code runs exactly once per process -- a second `import main` anywhere else in
# the same process is a no-op. The flag below documents that intent; the real safety net
# for the unusual edge case of a forced re-run (e.g. importlib.reload) is the try/except
# in _start_health_check_server above, which turns a would-be duplicate-bind crash into a
# clean log line instead -- verified: it does not take down the process.
_HEALTH_SERVER_STARTED = False
if not _HEALTH_SERVER_STARTED:
    threading.Thread(target=_start_health_check_server, daemon=True).start()
    _HEALTH_SERVER_STARTED = True
# ============================================
# End health check
# ============================================


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    # telegram.error.Conflict fires when Telegram sees a second getUpdates connection for
    # this bot token -- normal and expected for a few seconds during a Render redeploy,
    # while the old container is still shutting down and the new one has just started.
    # python-telegram-bot's polling loop already retries this indefinitely on its own and
    # does NOT crash the process; this branch only makes that visible and unambiguous in
    # the logs instead of it looking like an unexplained generic error.
    if isinstance(context.error, Conflict):
        logger.warning(
            "Telegram Conflict (409): another getUpdates connection is active for this "
            "bot token. This is expected for a few seconds during a Render redeploy and "
            "will resolve on its own once the old instance fully stops polling."
        )
        return

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
    try:
        # drop_pending_updates=True: on a Render redeploy, don't reprocess whatever
        # updates queued up in the few seconds between the old instance stopping and
        # this one starting -- avoids duplicate replies to messages sent during that gap.
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except Conflict:
        # Belt-and-suspenders: PTB's polling loop already retries Conflict internally
        # and routes it through on_error above without crashing. This branch only
        # matters if a Conflict is somehow raised outside that loop (e.g. during the
        # earliest bootstrap sliver, before the retry loop takes over). Exiting cleanly
        # here lets Render's process supervisor restart the container immediately,
        # which is the correct, expected recovery path -- rather than surfacing a raw,
        # unexplained traceback.
        logger.warning(
            "Startup hit a Telegram Conflict (another instance still holding the "
            "polling connection). Exiting so Render can restart cleanly; this should "
            "resolve on the next attempt once the old instance is fully stopped."
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
