"""
SocialPulse - Marketing-facing summary reports from the feature-rich dataset.
Sentiment by keyword/platform, topic prevalence by keyword, and engagement drivers.
"""

from pathlib import Path

import pandas as pd

FEATURES = Path("data/clean/features_dataset.csv")
OUT = Path("data/reports/features")


def _save(df: pd.DataFrame, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / name, index=False, encoding="utf-8-sig")
    print(f"  {name} ({len(df)} rows)")


def main() -> None:
    df = pd.read_csv(FEATURES)
    print("Writing feature reports:")

    # Sentiment by keyword + platform (English-only, where sentiment is reliable).
    rel = df[df["sentiment_label"] != "undetermined"]
    sent = (rel.groupby(["Platform", "Keyword", "sentiment_label"]).size()
            .reset_index(name="count"))
    sent["pct_within_group"] = (sent["count"] /
        sent.groupby(["Platform", "Keyword"])["count"].transform("sum") * 100).round(1)
    _save(sent.sort_values(["Platform", "Keyword"]), "sentiment_by_keyword.csv")

    # Topic reports exclude rows with no topic signal (OOV / non-English).
    topical = df[df["dominant_topic_label"] != "no_topic"]

    # Topic prevalence by keyword (audience-interest map).
    topic_kw = (topical.groupby(["Keyword", "dominant_topic_label"]).size()
                .reset_index(name="count").sort_values(["Keyword", "count"], ascending=[True, False]))
    _save(topic_kw, "topic_by_keyword.csv")

    # Engagement drivers: by topic and by sentiment (within-platform normalized).
    eng_topic = (topical.groupby("dominant_topic_label").agg(
        posts=("post_id", "size"),
        avg_engagement_pct=("engagement_pct_within_platform", "mean"),
        pct_high=("engagement_high", "mean")).round(3)
        .sort_values("avg_engagement_pct", ascending=False).reset_index())
    _save(eng_topic, "engagement_by_topic.csv")

    eng_sent = (rel.groupby("sentiment_label").agg(
        posts=("post_id", "size"),
        avg_engagement_pct=("engagement_pct_within_platform", "mean"),
        pct_high=("engagement_high", "mean")).round(3).reset_index())
    _save(eng_sent, "engagement_by_sentiment.csv")

    # Platform-level sentiment summary.
    plat = (rel.groupby(["Platform", "sentiment_label"]).size().reset_index(name="count"))
    _save(plat, "sentiment_by_platform.csv")

    print("Feature reports complete ->", OUT)


if __name__ == "__main__":
    main()
