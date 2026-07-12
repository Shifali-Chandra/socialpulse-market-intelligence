"""
SocialPulse - Week 5 time-series trend analysis.
Sentiment, volume, topic, and keyword trends over time from the feature dataset.
Windowed to the recent dense period (older YouTube comments are sparse).
"""

from pathlib import Path

import pandas as pd

FEATURES = Path("data/clean/features_dataset.csv")
OUT = Path("data/reports/trends")
RECENT_WEEKS = 12


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["Published Date"], errors="coerce")
    df = df.dropna(subset=["date"])
    cutoff = df["date"].max() - pd.Timedelta(weeks=RECENT_WEEKS)
    df = df[df["date"] >= cutoff].copy()
    df["week"] = df["date"].dt.to_period("W").apply(lambda p: p.start_time.date().isoformat())
    return df


def _save(df: pd.DataFrame, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / name, index=False, encoding="utf-8-sig")
    print(f"  {name} ({len(df)} rows)")


def volume_over_time(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["week", "Platform"]).size().reset_index(name="posts")


def sentiment_over_time(df: pd.DataFrame) -> pd.DataFrame:
    rel = df[df["sentiment_label"] != "undetermined"]
    g = rel.groupby(["week", "Platform", "sentiment_label"]).size().reset_index(name="count")
    g["share_pct"] = (g["count"] /
        g.groupby(["week", "Platform"])["count"].transform("sum") * 100).round(1)
    return g.sort_values(["Platform", "week", "sentiment_label"])


def topic_over_time(df: pd.DataFrame) -> pd.DataFrame:
    topical = df[df["dominant_topic_label"] != "no_topic"]
    return (topical.groupby(["week", "dominant_topic_label"]).size()
            .reset_index(name="posts").sort_values(["week", "posts"], ascending=[True, False]))


def emerging_topics(df: pd.DataFrame) -> pd.DataFrame:
    """Compare each topic's share in the recent half vs the earlier half of the window."""
    topical = df[df["dominant_topic_label"] != "no_topic"].copy()
    mid = topical["date"].min() + (topical["date"].max() - topical["date"].min()) / 2
    early = topical[topical["date"] < mid]
    late = topical[topical["date"] >= mid]
    e = early["dominant_topic_label"].value_counts(normalize=True)
    l = late["dominant_topic_label"].value_counts(normalize=True)
    out = pd.DataFrame({"early_share": e, "late_share": l}).fillna(0)
    out["change_pct_points"] = ((out["late_share"] - out["early_share"]) * 100).round(2)
    return out.sort_values("change_pct_points", ascending=False).reset_index(names="dominant_topic_label")


def keyword_over_time(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["week", "Keyword"]).size().reset_index(name="posts")


def main() -> None:
    df = _prep(pd.read_csv(FEATURES))
    print(f"Trend window: {df['date'].min().date()} -> {df['date'].max().date()} ({len(df)} dated posts, last {RECENT_WEEKS} weeks)")
    print("Writing trend tables:")
    _save(volume_over_time(df), "volume_over_time.csv")
    _save(sentiment_over_time(df), "sentiment_over_time.csv")
    _save(topic_over_time(df), "topic_over_time.csv")
    _save(emerging_topics(df), "emerging_topics.csv")
    _save(keyword_over_time(df), "keyword_over_time.csv")
    print("Trend analysis complete ->", OUT)


if __name__ == "__main__":
    main()
