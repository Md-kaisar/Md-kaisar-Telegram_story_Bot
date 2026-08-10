"""
Prompt templates for every MuseBot feature.
Keeping these centralized makes tone/quality consistent and easy to tune.
"""
from config import MUSEBOT_SYSTEM_PROMPT

LANGUAGE_INSTRUCTIONS = {
    "en": "Write entirely in English.",
    "ur": "Write entirely in Urdu script.",
    "ru": "Write entirely in Russian (Cyrillic script).",
}

JSON_ONLY = (
    "Respond with ONLY valid JSON. No markdown code fences, no preamble, "
    "no explanation — just the raw JSON object."
)


def _base(language: str, style_hint: str = "") -> str:
    lang_instr = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
    return f"{MUSEBOT_SYSTEM_PROMPT}\n\n{lang_instr}\n{style_hint}".strip()


def scene_description_prompt() -> str:
    return (
        "Look at this photo carefully. In 2-3 sentences, describe the scene, "
        "focusing on natural elements (sunset, mountains, river, flowers, rain, fog, "
        "clouds, birds, trees, ocean, stars, seasons, light, weather, textures) and the "
        "overall atmosphere. Be specific and sensory. Do not mention any people unless "
        "clearly present. Respond with plain description text only, nothing else."
    )


def poem_prompt(scene: str, style: str, language: str) -> str:
    return (
        f"{_base(language)}\n\n"
        f"Scene: {scene}\n\n"
        f"Write an original, unpublished poem (6-14 lines) inspired by this scene, "
        f"in the '{style}' style. {JSON_ONLY} with keys: "
        '"title" (a short evocative title), "poem" (the poem text with \\n line breaks), '
        '"mood" (one word describing the emotional tone), '
        '"reflection" (one short poetic one-line reflection, under 12 words).'
    )


def caption_prompt(scene: str, language: str) -> str:
    return (
        f"{_base(language)}\n\n"
        f"Scene: {scene}\n\n"
        f"Write 5 original Instagram captions inspired by this scene, one for each of these "
        f"categories: poetic, aesthetic, short, minimalist, deep. Each caption should be a "
        f"single line, under 15 words, no hashtags, no emojis unless truly fitting. "
        f"{JSON_ONLY} with keys exactly: \"poetic\", \"aesthetic\", \"short\", \"minimalist\", \"deep\"."
    )


def quote_prompt(scene: str, language: str) -> str:
    return (
        f"{_base(language)}\n\n"
        f"Scene: {scene}\n\n"
        f"Write ONE original, wise, quotable line inspired by this scene (under 20 words). "
        f"It should feel timeless, not like generic AI text. "
        f'{JSON_ONLY} with key "quote".'
    )


def haiku_prompt(scene: str, language: str) -> str:
    return (
        f"{_base(language)}\n\n"
        f"Scene: {scene}\n\n"
        f"Write one traditional haiku (5-7-5 syllable structure) inspired by this scene. "
        f'{JSON_ONLY} with keys "line1", "line2", "line3".'
    )


def mood_prompt(scene: str, moods: list[str]) -> str:
    mood_list = ", ".join(moods)
    return (
        f"{MUSEBOT_SYSTEM_PROMPT}\n\n"
        f"Scene: {scene}\n\n"
        f"Choose the single dominant mood this scene evokes from this exact list: "
        f"{mood_list}. Also estimate your confidence (0-100). "
        f'{JSON_ONLY} with keys "mood" (must be from the list) and "confidence" (integer).'
    )


def story_prompt(scene: str, genre: str, language: str) -> str:
    return (
        f"{_base(language)}\n\n"
        f"Scene: {scene}\n\n"
        f"Write an original short story (100-200 words) in the '{genre}' genre, inspired by "
        f"this scene. Give it a title. "
        f'{JSON_ONLY} with keys "title" and "story".'
    )


def prompts_prompt(scene: str, language: str) -> str:
    return (
        f"{_base(language)}\n\n"
        f"Scene: {scene}\n\n"
        f"Write 3 original, imaginative creative-writing prompts inspired by this scene. "
        f"Each should be a single evocative question or invitation to write, under 20 words. "
        f'{JSON_ONLY} with key "prompts" as an array of exactly 3 strings.'
    )


def palette_emotion_prompt(hex_colors: list[str]) -> str:
    colors = ", ".join(hex_colors)
    return (
        f"{MUSEBOT_SYSTEM_PROMPT}\n\n"
        f"Here are hex color codes extracted from a nature photo: {colors}\n\n"
        f"For each color, give a poetic but fitting color NAME (2-3 words, e.g. 'Forest Green') "
        f"and a single word or short phrase for the EMOTION it evokes (e.g. 'Stability'). "
        f'{JSON_ONLY} with key "colors" as an array of objects, each with keys '
        f'"hex", "name", "emotion", in the same order as given.'
    )
