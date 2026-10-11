import re
from typing import Literal

PreferenceKey = Literal["response_style", "language", "diet_preference", "exercise_preference"]
ALLOWED_VALUES = {
    "response_style": {"concise", "detailed"},
    "language": {"zh", "en"},
    "diet_preference": {"light", "vegetarian", "no_spicy"},
    "exercise_preference": {"walking", "running", "swimming", "cycling", "yoga"},
}
PHRASES = {
    "简短的回答": ("response_style", "concise"),
    "详细的回答": ("response_style", "detailed"),
    "清淡饮食": ("diet_preference", "light"),
    "素食": ("diet_preference", "vegetarian"),
    "不辣的食物": ("diet_preference", "no_spicy"),
    "散步": ("exercise_preference", "walking"),
    "跑步": ("exercise_preference", "running"),
    "游泳": ("exercise_preference", "swimming"),
    "骑行": ("exercise_preference", "cycling"),
    "瑜伽": ("exercise_preference", "yoga"),
}
FORGET_KEYS = {
    "回答风格": "response_style",
    "语言偏好": "language",
    "饮食偏好": "diet_preference",
    "运动偏好": "exercise_preference",
}


def extract_preferences(text: str) -> list[dict]:
    """Conservative exact grammar, current user text only. No free-form medical facts."""
    if any(character in text for character in ('"', "'", "“", "”", "‘", "’", "`", ">")):
        return []  # quoted documents/instructions are not memory consent
    changes = {}
    for sentence in re.split(r"[。；;\n]", text):
        sentence = sentence.strip().rstrip("！!.")
        match = re.fullmatch(r"请记住[：:]?\s*我(?:现在)?(?:更)?(?:喜欢|偏好)(.+)", sentence)
        if match and match[1] in PHRASES:
            key, value = PHRASES[match[1]]
            changes[key] = value
        language = re.fullmatch(r"以后请用(中文|英文)回答", sentence)
        if language:
            changes["language"] = "zh" if language[1] == "中文" else "en"
        forget = re.fullmatch(r"请忘记[：:]?\s*我的(.+)", sentence)
        if forget and forget[1] in FORGET_KEYS:
            changes[FORGET_KEYS[forget[1]]] = None
    return [{"key": key, "value": value} for key, value in changes.items()]
