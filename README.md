# 🌿 MuseBot — AI Poetry & Nature Companion

A Telegram bot that turns nature photographs into original poems, captions, quotes,
haiku, short stories, color palettes, and writing prompts — powered by Google Gemini.

## Features

- **Photo → Poem**: scene analysis via Gemini Vision, then an original poem in your chosen style
- **Instagram Captions**: 5 captions across poetic / aesthetic / short / minimalist / deep
- **Quote Generator**, **Haiku Generator (5-7-5)**, **Mood Detection** with confidence bar
- **Short Story Writer** across 5 genres (fantasy, slice of life, magical realism, adventure, philosophical)
- **Real Color Palette Extraction** — actual dominant colors pulled from the pixels (not guessed), each named and given an emotion by the AI
- **Writing Prompts** (3 per photo)
- **10 poem styles** (Romantic, Nature, Classic, Modern, Japanese, Shakespearean, Urdu-inspired, Free Verse, Minimalist, Philosophical)
- **3 languages**: English, Urdu, Russian
- History, Favorites, Share, and a Stats dashboard
- Per-user daily generation cap to protect the Gemini free tier
- Inline "Do all of the above ✨" button to run every text feature on one photo in one tap

### Extras added beyond the original spec
- **Real pixel-based palette extraction** (Pillow median-cut quantization) instead of asking the AI to guess colors — much more accurate, with AI only used for the poetic naming/emotion layer
- **Scene-description caching** per photo so multiple actions on the same image only call Gemini Vision once
- **`/stats` command** — total creations, breakdown by type, most frequent mood, favorites count
- **`/favorites` command** — list all saved favorites, not just save the latest
- Robust JSON parsing that tolerates minor formatting quirks in model output
- Friendly rate limiting with a clear in-character message instead of silent failures
- **Admin new-user notifications** — set `ADMIN_CHAT_ID` in `.env` (your own numeric Telegram
  ID, from `@userinfobot`) and you get DMed once per new person who starts the bot, e.g.
  `🌱 New MuseBot user: @someusername (ID: 123456789)`. Returning users don't re-trigger it,
  and leaving it unset simply disables the feature — no errors either way.

## Project Structure

```
musebot/
├── main.py                  # entry point, wires up all handlers
├── config.py                 # env vars, constants, styles/languages/moods
├── requirements.txt
├── .env.example
├── Procfile                  # for Railway/Render
├── database/
│   └── db.py                 # SQLite: users, history, favorites, usage
├── services/
│   ├── ai_service.py          # Gemini text + vision calls, JSON parsing
│   ├── palette_service.py     # real color extraction from image bytes
│   └── prompts.py             # all prompt templates in one place
├── handlers/
│   ├── start.py               # /start /help /style /language
│   ├── photo.py                # photo intake + standalone /poem /caption etc.
│   ├── actions.py              # shared dispatcher for every creative action
│   ├── callbacks.py            # inline button router
│   └── history.py              # /history /favorite /favorites /share /stats
└── utils/
    ├── keyboards.py            # inline keyboard builders
    ├── formatting.py           # MarkdownV2-safe message formatting
    ├── image_cache.py          # short-key in-memory photo/scene cache
    └── ratelimit.py            # per-user daily usage cap
```

## Setup

1. **Get a Telegram bot token** from [@BotFather](https://t.me/BotFather).
2. **Get a free Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey).
3. Clone/copy this project, then:

```bash
cd musebot
python -m venv .venv && source .venv/Scripts/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste in your TELEGRAM_BOT_TOKEN and GEMINI_API_KEY
python main.py
```

The bot will start polling immediately — message it on Telegram and send a nature photo.

## Deployment

### Railway / Render
1. Push this folder to a GitHub repo.
2. Create a new Railway/Render **worker/background service** from the repo.
3. Set `TELEGRAM_BOT_TOKEN` and `GEMINI_API_KEY` as environment variables in the dashboard.
4. The included `Procfile` (`worker: python main.py`) tells the platform how to run it.
5. Note: SQLite lives on local disk — on most PaaS free tiers this resets on redeploy.
   For persistent history across deploys, attach a volume or switch `DB_PATH` to a mounted disk,
   or migrate `database/db.py` to PostgreSQL (the function signatures are designed to make that swap straightforward).

### VPS
Run under `systemd` or `pm2`/`supervisor` pointing at `python main.py` inside the project's venv.

## Troubleshooting

**`404 NOT_FOUND` / "no longer available to new users" for a model:** as of mid-2026, Google
has been retiring Gemini Flash model IDs faster than their own deprecation schedule
suggests, and availability sometimes differs by API key age. To stop this from breaking
the bot every time Google retires a model string, `services/ai_service.py` now tries an
ordered list of fallback models automatically (`gemini-3.5-flash` → `gemini-2.5-flash` →
`gemini-flash-latest` → `gemini-3.1-flash-lite`) and remembers whichever one works, instead
of hard-failing on the first one. If ALL of these are ever retired too, add the current
model name from https://ai.google.dev/gemini-api/docs/models to the top of
`_TEXT_CANDIDATES` / `_VISION_CANDIDATES` in `services/ai_service.py`, or set
`GEMINI_TEXT_MODEL` / `GEMINI_VISION_MODEL` in `.env`.

**`429 RESOURCE_EXHAUSTED` with `limit: 0` for a specific model:** this is different from a normal
rate limit — `limit: 0` means that exact model has **no free-tier quota at all** for your key
(usually because it's been superseded). As of testing this project, both `gemini-2.0-flash`
*and* `gemini-2.5-flash-lite` are confirmed dead for new keys — don't set either of those in
`.env`. This is exactly what the fallback chain above exists to handle automatically; if you
see this in the logs, check the next line for `"switched to '...'"` — that means it already
recovered on its own. If it didn't recover, check
https://ai.google.dev/gemini-api/docs/rate-limits for the current free-tier model list and
update `_TEXT_CANDIDATES`/`_VISION_CANDIDATES` in `services/ai_service.py`.

**"Something clouded my thoughts" on every single action:** This almost always means every
Gemini call is failing. The most common causes, in order of likelihood:
1. `GEMINI_API_KEY` isn't set correctly in `.env` (or `.env` wasn't loaded because you ran
   `python main.py` from the wrong directory).
2. The key is invalid, expired, or has no quota left.
3. Your `google-genai` package version is out of date — run `pip install -U google-genai`.

To see the *real* error (not just the friendly in-chat message), check the terminal where
`python main.py` is running — every failure is logged there with a full traceback via
`logger.exception(...)` in `services/ai_service.py`. That traceback will tell you exactly
what Google's API rejected.

**Note on the AI SDK:** this project uses the current `google-genai` package (`from google import
genai`, `client.models.generate_content(...)`). Google fully deprecated the older
`google-generativeai` package (`import google.generativeai as genai`) — if you see references
to that package anywhere or install it by mistake, replace it; its API calls no longer work
reliably.

## Notes on quality & safety

- All creative output is generated fresh per request — MuseBot never reproduces existing
  copyrighted poems, song lyrics, or quotes; every prompt explicitly instructs originality.
- The bot never assumes romantic intent from a photo or message, per the product's personality spec.
- MarkdownV2 escaping is applied everywhere so special characters in AI output can't break message rendering.

## Extending further (ideas)

- Add `/leaderboard` with shared (opt-in) creations across all users
- Export a user's favorites as a PDF chapbook (Anthropic's PDF tooling makes this easy to bolt on)
- Add scheduled "photo of the day" prompts via `JobQueue`
- Swap SQLite for PostgreSQL for multi-instance deployments
