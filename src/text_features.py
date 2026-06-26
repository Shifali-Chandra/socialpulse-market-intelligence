"""
SocialPulse - Text feature extraction.
Language detection, a modeling-ready clean_text, and structural text counts.
Reuses _clean_social_text from data_cleaner so cleaning stays single-sourced.
"""

import html
import re

import pandas as pd
from langdetect import DetectorFactory, detect

from data_cleaner import _clean_social_text

DetectorFactory.seed = 42

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_MENTION_RE = re.compile(r"@\w+")
_HASHTAG_RE = re.compile(r"#\w+")
_EMOJI_RE = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f000-\U0001f0ff\U00002190-\U000021ff]"
)


def detect_language(text: str) -> str:
    """Detect language code, returning 'unknown' on empty/emoji-only/short text."""
    t = str(text).strip()
    if len(t) < 3:
        return "unknown"
    try:
        return detect(t)
    except Exception:
        return "unknown"


def clean_social_cased(text: str) -> str:
    """HTML-decoded, URL/mention/hashtag-symbol-stripped text (case preserved)."""
    return _clean_social_text(html.unescape(str(text)))


def clean_for_modeling(text: str) -> str:
    """Lowercased variant for TF-IDF and topic/sentiment models."""
    return clean_social_cased(text).lower()


def _structural_counts(text: str) -> dict:
    t = str(text)
    words = t.split()
    n_words = len(words)
    letters = [c for c in t if c.isalpha()]
    uppercase_ratio = sum(c.isupper() for c in letters) / len(letters) if letters else 0.0
    return {
        "char_len": len(t),
        "word_count": n_words,
        "avg_word_len": round(sum(len(w) for w in words) / n_words, 2) if n_words else 0.0,
        "hashtag_count": len(_HASHTAG_RE.findall(t)),
        "mention_count": len(_MENTION_RE.findall(t)),
        "url_count": len(_URL_RE.findall(t)),
        "emoji_count": len(_EMOJI_RE.findall(t)),
        "uppercase_ratio": round(uppercase_ratio, 3),
        "exclaim_count": t.count("!"),
        "question_count": t.count("?"),
    }


def add_text_features(df: pd.DataFrame, text_col: str = "Content") -> pd.DataFrame:
    """Add clean_text, lang, sentiment_reliable, and structural count columns."""
    df = df.copy()
    raw = df[text_col].fillna("").astype(str)
    df["clean_text"] = raw.apply(clean_for_modeling)
    df["clean_text_cased"] = raw.apply(clean_social_cased)  # case/emoji preserved for lexicon sentiment
    df["lang"] = raw.apply(detect_language)
    df["sentiment_reliable"] = df["lang"] == "en"
    counts = raw.apply(_structural_counts).apply(pd.Series)
    return pd.concat([df, counts], axis=1)
