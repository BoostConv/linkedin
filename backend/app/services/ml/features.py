"""Feature extraction from posts for ML scoring model."""
import re
from datetime import datetime


def extract_features(post_data: dict) -> dict:
    """Extract ML features from a post record.

    Args:
        post_data: Dict with post fields (content, format, hook_pattern, etc.)

    Returns:
        Dict of feature_name -> numeric_value
    """
    content = post_data.get("content", "")
    features = {}

    # Content features
    features["word_count"] = len(content.split())
    features["char_count"] = len(content)
    features["paragraph_count"] = len([p for p in content.split("\n\n") if p.strip()])
    features["line_count"] = len([l for l in content.split("\n") if l.strip()])

    # Sentence analysis
    sentences = re.split(r"[.!?]+", content)
    sentences = [s.strip() for s in sentences if s.strip()]
    features["sentence_count"] = len(sentences)
    if sentences:
        lengths = [len(s.split()) for s in sentences]
        features["avg_sentence_length"] = sum(lengths) / len(lengths)
        features["min_sentence_length"] = min(lengths)
        features["max_sentence_length"] = max(lengths)
        features["sentence_length_variance"] = (
            sum((l - features["avg_sentence_length"]) ** 2 for l in lengths) / len(lengths)
        )
    else:
        features["avg_sentence_length"] = 0
        features["min_sentence_length"] = 0
        features["max_sentence_length"] = 0
        features["sentence_length_variance"] = 0

    # Format encoding
    fmt = post_data.get("format", "text")
    features["is_text"] = 1 if fmt == "text" else 0
    features["is_carousel"] = 1 if fmt == "carousel" else 0
    features["is_image_text"] = 1 if fmt == "image_text" else 0

    # Hook pattern encoding
    hook_patterns = ["contrarian", "data_bomb", "story_open", "question", "liste", "avant_apres", "bold_claim"]
    hook = post_data.get("hook_pattern", "")
    for p in hook_patterns:
        features[f"hook_{p}"] = 1 if hook == p else 0

    # CTA type encoding
    cta_types = ["engagement", "save", "dm", "question"]
    cta = post_data.get("cta_type", "")
    for c in cta_types:
        features[f"cta_{c}"] = 1 if cta == c else 0

    # Content signals
    features["has_numbers"] = 1 if re.search(r"\d+%?", content) else 0
    features["number_count"] = len(re.findall(r"\d+%?", content))
    features["has_emoji"] = 1 if re.search(r"[\U0001f600-\U0001f9ff]", content) else 0
    features["emoji_count"] = len(re.findall(r"[\U0001f600-\U0001f9ff]", content))
    features["has_question"] = 1 if "?" in content else 0
    features["question_count"] = content.count("?")
    features["has_list"] = 1 if re.search(r"^\s*[-•]\s", content, re.MULTILINE) else 0
    features["has_parentheses"] = 1 if "(" in content else 0

    # Scheduling features
    scheduled_at = post_data.get("scheduled_at")
    if scheduled_at:
        if isinstance(scheduled_at, str):
            scheduled_at = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        features["hour_of_day"] = scheduled_at.hour
        features["day_of_week"] = scheduled_at.weekday()
        features["is_morning"] = 1 if 7 <= scheduled_at.hour <= 9 else 0
        features["is_lunch"] = 1 if 11 <= scheduled_at.hour <= 13 else 0
        features["is_evening"] = 1 if 17 <= scheduled_at.hour <= 19 else 0
    else:
        features["hour_of_day"] = -1
        features["day_of_week"] = -1
        features["is_morning"] = 0
        features["is_lunch"] = 0
        features["is_evening"] = 0

    # Anti-AI score
    features["anti_ai_score"] = post_data.get("anti_ai_score", 0) or 0

    return features


FEATURE_NAMES = [
    "word_count", "char_count", "paragraph_count", "line_count",
    "sentence_count", "avg_sentence_length", "min_sentence_length",
    "max_sentence_length", "sentence_length_variance",
    "is_text", "is_carousel", "is_image_text",
    "hook_contrarian", "hook_data_bomb", "hook_story_open", "hook_question",
    "hook_liste", "hook_avant_apres", "hook_bold_claim",
    "cta_engagement", "cta_save", "cta_dm", "cta_question",
    "has_numbers", "number_count", "has_emoji", "emoji_count",
    "has_question", "question_count", "has_list", "has_parentheses",
    "hour_of_day", "day_of_week", "is_morning", "is_lunch", "is_evening",
    "anti_ai_score",
]
