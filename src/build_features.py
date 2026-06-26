"""
SocialPulse - Feature-engineering orchestrator.
unified_dataset.csv -> text features -> sentiment -> topics -> embeddings ->
engagement -> assembled one-row-per-post feature-rich dataset (features_dataset.csv).
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")

from text_features import add_text_features
from sentiment_model import add_lexicon_sentiment
from engagement_features import add_engagement_features
import topic_model

FEATURE_COLUMNS = [
    "post_id", "Platform", "Keyword", "Author", "Published Date", "Content", "clean_text",
    "lang", "sentiment_reliable", "char_len", "word_count", "avg_word_len", "hashtag_count",
    "mention_count", "url_count", "emoji_count", "uppercase_ratio", "exclaim_count",
    "question_count", "vader_compound", "textblob_polarity", "textblob_subjectivity",
    "sentiment_label", "sentiment_score", "sentiment_model", "dominant_topic_id",
    "dominant_topic_label", "topic_weight", "engagement_raw", "engagement_log",
    "engagement_pct_within_platform", "engagement_high", "engagement_tier",
    "pub_year", "pub_month", "pub_dayofweek", "pub_is_weekend",
]


def _add_date_parts(df: pd.DataFrame) -> pd.DataFrame:
    dt = pd.to_datetime(df["Published Date"], errors="coerce")
    df["pub_year"] = dt.dt.year
    df["pub_month"] = dt.dt.month
    df["pub_dayofweek"] = dt.dt.dayofweek
    df["pub_is_weekend"] = dt.dt.dayofweek.isin([5, 6]).astype("Int64")
    return df


def main() -> None:
    src = Path("data/clean/unified_dataset.csv")
    out = Path("data/clean/features_dataset.csv")
    df = pd.read_csv(src)
    print(f"Loaded {len(df)} unified rows.")

    df = df[df["Content"].notna() & (df["Content"].astype(str).str.strip() != "")].reset_index(drop=True)
    df.insert(0, "post_id", range(len(df)))
    print(f"After dropping empty Content: {len(df)} rows.")

    print("1/5 text features...")
    df = add_text_features(df)
    print("2/5 lexicon sentiment (VADER + TextBlob)...")
    df = add_lexicon_sentiment(df)
    print("3/5 topic model + embeddings...")
    df, best_k, _ = topic_model.run(df)
    print(f"   topics fitted: k={best_k}")
    print("4/5 engagement features...")
    df = add_engagement_features(df)
    print("5/5 date parts...")
    df = _add_date_parts(df)

    cols = [c for c in FEATURE_COLUMNS if c in df.columns]
    df[cols].to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\nFeature-rich dataset: {out} ({len(df)} rows, {len(cols)} columns)")
    print("Sentiment label dist:", df["sentiment_label"].value_counts().to_dict())
    print("Engagement tier dist:", df["engagement_tier"].value_counts().to_dict())


if __name__ == "__main__":
    main()
