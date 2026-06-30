"""
SocialPulse - auto-generated key-findings summary (facts only).
Rolls up the feature dataset and model-eval reports into a current insights_summary.md.
Interpretation and marketing recommendations stay in the human-authored final report.
"""

from pathlib import Path

import pandas as pd

FEATURES = Path("data/clean/features_dataset.csv")
EVAL = Path("data/reports/model_eval")
TRENDS = Path("data/reports/trends")
OUT = Path("data/reports/insights_summary.md")


def _read(path):
    return pd.read_csv(path) if path.exists() else None


def main() -> None:
    df = pd.read_csv(FEATURES)
    df["date"] = pd.to_datetime(df["Published Date"], errors="coerce")
    lines = ["# Key Findings (auto-generated)", "",
             "Factual rollup of the current feature dataset. Interpretation lives in the final report.", ""]

    # Overview
    lines.append("## Overview")
    lines.append(f"- Posts: {len(df):,} across {df['Platform'].nunique()} platforms "
                 f"({', '.join(f'{p}: {n:,}' for p, n in df['Platform'].value_counts().items())}).")
    lines.append(f"- Content date range: {df['date'].min().date()} to {df['date'].max().date()}.")
    lines.append("")

    # Sentiment per platform (English only)
    rel = df[df["sentiment_label"] != "undetermined"]
    lines.append("## Sentiment by platform (English)")
    for p, g in rel.groupby("Platform"):
        share = (g["sentiment_label"].value_counts(normalize=True) * 100).round(1)
        lines.append(f"- {p}: positive {share.get('positive', 0)}%, "
                     f"neutral {share.get('neutral', 0)}%, negative {share.get('negative', 0)}%.")
    lines.append("")

    # Engagement vs sentiment (is it flat?)
    eng = rel.groupby("sentiment_label")["engagement_pct_within_platform"].mean().round(3)
    spread = round(eng.max() - eng.min(), 3)
    rel_word = "essentially flat (sentiment does not predict engagement)" if spread < 0.05 else "varies with sentiment"
    lines.append("## Engagement vs sentiment")
    lines.append(f"- Avg engagement percentile by sentiment: " +
                 ", ".join(f"{k} {v}" for k, v in eng.items()) + f" (spread {spread}).")
    lines.append(f"- Relationship is {rel_word}.")
    lines.append("")

    # Dominant topics
    topical = df[df["dominant_topic_label"] != "no_topic"]
    lines.append("## Dominant topics (by volume)")
    for label, n in topical["dominant_topic_label"].value_counts().head(5).items():
        lines.append(f"- {label} - {n:,} posts.")
    lines.append("")

    # Emerging topics (if trend output exists)
    em = _read(TRENDS / "emerging_topics.csv")
    if em is not None and len(em):
        lines.append("## Emerging vs declining topics (recent vs earlier in window)")
        top = em.head(3); bot = em.tail(2)
        for _, r in top.iterrows():
            lines.append(f"- Rising: {r['dominant_topic_label']} ({r['change_pct_points']:+} pts).")
        for _, r in bot.iterrows():
            lines.append(f"- Declining: {r['dominant_topic_label']} ({r['change_pct_points']:+} pts).")
        lines.append("")

    # Top keywords
    lines.append("## Top keywords (by volume)")
    for kw, n in df["Keyword"].value_counts().head(5).items():
        lines.append(f"- {kw} - {n:,} posts.")
    lines.append("")

    # Model facts
    lines.append("## Models")
    gold = _read(EVAL / "sentiment_gold_eval.csv")
    if gold is not None and len(gold):
        best = gold.sort_values("macro_f1", ascending=False).iloc[0]
        lines.append(f"- Production sentiment model: {best['model']} "
                     f"(deploy-domain macro-F1 {best['macro_f1']}).")
    tev = _read(EVAL / "topic_model_eval.csv")
    if tev is not None and len(tev):
        nmf = tev[tev["model"] == "nmf"].iloc[0]
        lines.append(f"- Topic model: NMF, k={int(nmf['k'])}, UMass coherence {nmf['umass_coherence']} "
                     f"(more coherent than LDA).")
    lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Insights summary written: {OUT}")


if __name__ == "__main__":
    main()
