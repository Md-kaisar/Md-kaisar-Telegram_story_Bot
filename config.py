"""
MuseBot configuration.
Loads secrets/settings from environment variables (.env supported via python-dotenv).
"""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Gemini models (current on the google-genai SDK). Google has been retiring Flash models
# faster than their own deprecation dates suggest, so ai_service.py also maintains an
# automatic fallback chain -- these are just the *first* model tried.
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.5-flash")
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-3.5-flash")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "data", "musebot.db"))

# If set, MuseBot will DM this Telegram chat ID whenever a new user starts the bot.
# Get your own numeric ID by messaging @userinfobot on Telegram, then set it here.
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# Directory to temporarily store downloaded photos for palette extraction
TMP_DIR = os.getenv("TMP_DIR", os.path.join(os.path.dirname(__file__), "data", "tmp"))
os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Supported languages: code -> display name
LANGUAGES = {
    "en": "English 🇬🇧",
    "ur": "Urdu 🌙",
    "ru": "Russian 🇷🇺",
}
DEFAULT_LANGUAGE = "en"

# Supported poem styles
STYLES = [
    "Romantic",
    "Nature",
    "Classic",
    "Modern",
    "Japanese",
    "Shakespearean",
    "Urdu-inspired",
    "Free Verse",
    "Minimalist",
    "Philosophical",
]
DEFAULT_STYLE = "Nature"

# Story genres
STORY_GENRES = [
    "Fantasy",
    "Slice of Life",
    "Magical Realism",
    "Adventure",
    "Philosophical",
]

MOODS = [
    "calm", "nostalgic", "hopeful", "dreamy", "joyful",
    "lonely", "mysterious", "adventurous", "serene", "refreshing",
]

CAPTION_CATEGORIES = ["poetic", "aesthetic", "short", "minimalist", "deep"]

# Simple daily-use soft limits to protect the free Gemini tier (per user, per day)
# Simple daily-use soft limits to protect the free Gemini tier (per user, per day).
# Flash-Lite's free tier allows up to ~1,000 requests/day total across all users of
# this key, so keep this well under that if you expect multiple people using the bot.
DAILY_GENERATION_LIMIT = int(os.getenv("DAILY_GENERATION_LIMIT", "40"))

MUSEBOT_SYSTEM_PROMPT = """You are MuseBot, a thoughtful AI companion inspired by nature, \
literature, and quiet reflection. Your purpose is to help users appreciate the beauty in \
ordinary moments by creating original poems, captions, stories, and reflections based on \
their photos or prompts. Never copy existing poems or quotes. Keep your tone warm, \
imaginative, and emotionally grounded. Do not assume romantic intent or personal \
relationships. Celebrate nature, creativity, and human expression. Adapt your writing \
style to the user's selected preference while remaining original and respectful. Avoid \
clichés, overly dramatic romance, fake or exaggerated praise, and repetitive wording."""
