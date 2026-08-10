"""
Thin wrapper around Google Gemini for MuseBot, using the current `google-genai` SDK
(the old `google-generativeai` package is fully deprecated/archived and its API
calls will fail -- see https://github.com/google-gemini/deprecated-generative-ai-python).

Every generation function returns clean Python data (dict/str), already parsed
from the model's JSON response, with sane fallbacks if parsing fails.
"""
import json
import logging
import re
import threading

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_TEXT_MODEL, GEMINI_VISION_MODEL, MOODS
from services import prompts

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=GEMINI_API_KEY)

# Google has been retiring Gemini Flash model IDs faster than their own published
# shutdown dates, and availability can also differ by API key age. Rather than hard-code
# one model string and break every time Google retires it, we try a small ordered list
# of candidates and fall back automatically.
#
# 404 (NOT_FOUND / "no longer available") is permanent for this process's lifetime, so
# that model is remembered as dead and skipped entirely afterward -- no point re-probing
# it on every single call. 429 (RESOURCE_EXHAUSTED) is transient (a per-minute quota),
# so it is NOT blacklisted; we just try the next candidate for *this* call and the
# original model remains eligible again once its quota window resets.
#
# _active_model / _dead_models are shared across concurrent worker threads (each Gemini
# call runs via asyncio.to_thread), so all reads/writes go through _state_lock to avoid
# the two threads racing to update the same variable.
def _dedupe(seq):
    seen, out = set(), []
    for s in seq:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


_TEXT_CANDIDATES = _dedupe([GEMINI_TEXT_MODEL, "gemini-3.5-flash", "gemini-2.5-flash",
                             "gemini-flash-latest", "gemini-3.1-flash-lite"])
_VISION_CANDIDATES = _dedupe([GEMINI_VISION_MODEL, "gemini-3.5-flash", "gemini-2.5-flash",
                               "gemini-flash-latest", "gemini-3.1-flash-lite"])

_state_lock = threading.Lock()
_active_text_model = _TEXT_CANDIDATES[0]
_active_vision_model = _VISION_CANDIDATES[0]
_dead_models: set = set()  # models that returned 404 -- permanently skipped this run


def _is_not_found(e: Exception) -> bool:
    msg = str(e)
    return "NOT_FOUND" in msg or "404" in msg


def _is_rate_limited(e: Exception) -> bool:
    msg = str(e)
    return "RESOURCE_EXHAUSTED" in msg or "429" in msg


def _candidates_for(kind: str) -> list:
    with _state_lock:
        active = _active_text_model if kind == "text" else _active_vision_model
        pool = _TEXT_CANDIDATES if kind == "text" else _VISION_CANDIDATES
        dead = set(_dead_models)
    ordered = _dedupe([active] + pool)
    return [m for m in ordered if m not in dead]


class AIError(Exception):
    pass


def _extract_json(raw: str) -> dict:
    """Gemini sometimes wraps JSON in markdown fences despite instructions; strip and parse."""
    text = raw.strip()
    text = re.sub(r"^```(json)?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    text = text.strip()
    # Grab the outermost {...} in case there's stray text around it
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    # strict=False tolerates literal control characters (e.g. raw newlines) inside
    # string values, which Gemini occasionally emits despite JSON instructions.
    return json.loads(text, strict=False)


def _generate_text(prompt: str) -> str:
    global _active_text_model
    last_err = None
    for model in _candidates_for("text"):
        try:
            response = _client.models.generate_content(model=model, contents=prompt)
            with _state_lock:
                if model != _active_text_model:
                    logger.info("Text model switched to '%s'", model)
                _active_text_model = model
            return response.text
        except Exception as e:
            last_err = e
            if _is_not_found(e):
                with _state_lock:
                    _dead_models.add(model)
                logger.warning("Text model '%s' is permanently unavailable (404), blacklisting it: %s", model, e)
                continue
            if _is_rate_limited(e):
                logger.warning("Text model '%s' is rate-limited right now, trying next candidate: %s", model, e)
                continue
            logger.exception("Gemini text generation failed with a non-recoverable error")
            raise AIError(str(e)) from e
    logger.exception("All candidate text models failed")
    raise AIError(str(last_err)) from last_err


def _generate_json(prompt: str) -> dict:
    raw = _generate_text(prompt)
    try:
        return _extract_json(raw)
    except Exception:
        logger.warning("Failed to parse JSON from model, raw output: %s", raw[:500])
        raise AIError("The model returned an unexpected format. Please try again.")


def describe_scene(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Use Gemini Vision to produce a rich natural-language scene description."""
    global _active_vision_model
    last_err = None
    for model in _candidates_for("vision"):
        try:
            response = _client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompts.scene_description_prompt(),
                ],
            )
            with _state_lock:
                if model != _active_vision_model:
                    logger.info("Vision model switched to '%s'", model)
                _active_vision_model = model
            return response.text.strip()
        except Exception as e:
            last_err = e
            if _is_not_found(e):
                with _state_lock:
                    _dead_models.add(model)
                logger.warning("Vision model '%s' is permanently unavailable (404), blacklisting it: %s", model, e)
                continue
            if _is_rate_limited(e):
                logger.warning("Vision model '%s' is rate-limited right now, trying next candidate: %s", model, e)
                continue
            logger.exception("Gemini vision analysis failed with a non-recoverable error")
            raise AIError(str(e)) from e
    logger.exception("All candidate vision models failed")
    raise AIError(str(last_err)) from last_err


def generate_poem(scene: str, style: str, language: str) -> dict:
    data = _generate_json(prompts.poem_prompt(scene, style, language))
    return {
        "title": data.get("title", "Untitled"),
        "poem": data.get("poem", ""),
        "mood": data.get("mood", "reflective"),
        "reflection": data.get("reflection", ""),
    }


def generate_captions(scene: str, language: str) -> dict:
    data = _generate_json(prompts.caption_prompt(scene, language))
    return {k: data.get(k, "") for k in ["poetic", "aesthetic", "short", "minimalist", "deep"]}


def generate_quote(scene: str, language: str) -> str:
    data = _generate_json(prompts.quote_prompt(scene, language))
    return data.get("quote", "")


def generate_haiku(scene: str, language: str) -> dict:
    data = _generate_json(prompts.haiku_prompt(scene, language))
    return {
        "line1": data.get("line1", ""),
        "line2": data.get("line2", ""),
        "line3": data.get("line3", ""),
    }


def generate_mood(scene: str) -> dict:
    data = _generate_json(prompts.mood_prompt(scene, MOODS))
    mood = data.get("mood", "calm")
    if mood not in MOODS:
        mood = "calm"
    confidence = data.get("confidence", 70)
    try:
        confidence = int(confidence)
    except (TypeError, ValueError):
        confidence = 70
    return {"mood": mood, "confidence": max(0, min(100, confidence))}


def generate_story(scene: str, genre: str, language: str) -> dict:
    data = _generate_json(prompts.story_prompt(scene, genre, language))
    return {"title": data.get("title", "Untitled"), "story": data.get("story", "")}


def generate_prompts(scene: str, language: str) -> list:
    data = _generate_json(prompts.prompts_prompt(scene, language))
    result = data.get("prompts", [])
    if not isinstance(result, list):
        result = []
    return result[:3]


def generate_palette_meanings(hex_colors: list) -> list:
    data = _generate_json(prompts.palette_emotion_prompt(hex_colors))
    colors = data.get("colors", [])
    if not isinstance(colors, list):
        colors = [{"hex": h, "name": h, "emotion": "Wonder"} for h in hex_colors]
    return colors
