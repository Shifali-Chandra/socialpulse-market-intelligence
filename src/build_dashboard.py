"""
SocialPulse - build a self-contained interactive dashboard (Plotly HTML).
Reads the feature dataset and trend/feature reports and writes a single
data/reports/dashboard.html (opens in any browser, no server needed).
"""

import argparse
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CLEAN = Path("data/clean")
TRENDS = Path("data/reports/trends")
FEAT = Path("data/reports/features")
OUT = Path("data/reports/dashboard.html")

MUTED = px.colors.qualitative.Set2


def _fig_volume() -> go.Figure:
    v = pd.read_csv(TRENDS / "volume_over_time.csv")
    fig = px.line(v, x="week", y="posts", color="Platform", markers=True,
                  title="Post volume per week by platform", color_discrete_sequence=MUTED)
    fig.update_layout(xaxis_title="week", yaxis_title="posts")
    return fig


def _fig_sentiment_time() -> go.Figure:
    s = pd.read_csv(TRENDS / "sentiment_over_time.csv")
    pos = s[s["sentiment_label"] == "positive"]
    fig = px.line(pos, x="week", y="share_pct", color="Platform", markers=True,
                  title="Positive sentiment share (%) over time", color_discrete_sequence=MUTED)
    fig.update_layout(xaxis_title="week", yaxis_title="positive %")
    return fig


def _fig_sentiment_platform() -> go.Figure:
    sp = pd.read_csv(FEAT / "sentiment_by_platform.csv")
    fig = px.bar(sp, x="Platform", y="count", color="sentiment_label", barmode="stack",
                 title="Sentiment distribution by platform",
                 color_discrete_map={"positive": "#55a868", "neutral": "#8c8c8c", "negative": "#c44e52"})
    fig.update_layout(yaxis_title="posts")
    return fig


def _fig_top_topics(df: pd.DataFrame) -> go.Figure:
    t = df[df["dominant_topic_label"] != "no_topic"]["dominant_topic_label"].value_counts().head(10)
    fig = px.bar(x=t.values, y=t.index, orientation="h", title="Top topics by volume",
                 color_discrete_sequence=["#4c72b0"])
    fig.update_layout(xaxis_title="posts", yaxis_title="", yaxis=dict(autorange="reversed"))
    return fig


def _fig_emerging() -> go.Figure:
    em = pd.read_csv(TRENDS / "emerging_topics.csv").sort_values("change_pct_points")
    colors = ["#c44e52" if v < 0 else "#55a868" for v in em["change_pct_points"]]
    fig = go.Figure(go.Bar(x=em["change_pct_points"], y=em["dominant_topic_label"],
                           orientation="h", marker_color=colors))
    fig.update_layout(title="Emerging (green) vs declining (red) topics",
                      xaxis_title="change in share (pct points)")
    return fig


def _fig_keywords(df: pd.DataFrame) -> go.Figure:
    k = df["Keyword"].value_counts().head(12)
    fig = px.bar(x=k.values, y=k.index, orientation="h", title="Audience interest: keyword volume",
                 color_discrete_sequence=["#dd8452"])
    fig.update_layout(xaxis_title="posts", yaxis_title="", yaxis=dict(autorange="reversed"))
    return fig


def _fig_engagement_sentiment() -> go.Figure:
    e = pd.read_csv(FEAT / "engagement_by_sentiment.csv")
    fig = px.bar(e, x="sentiment_label", y="avg_engagement_pct",
                 title="Avg engagement percentile by sentiment (note: flat)",
                 color_discrete_sequence=["#937860"])
    fig.update_layout(yaxis_title="avg engagement percentile", yaxis_range=[0, 1])
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the interactive dashboard HTML.")
    parser.add_argument("--cdn", action="store_true",
                        help="Load Plotly.js from CDN (small file, needs internet) instead of inline (offline).")
    args = parser.parse_args()
    plotlyjs = "cdn" if args.cdn else "inline"

    df = pd.read_csv(CLEAN / "features_dataset.csv")
    figs = [
        _fig_volume(), _fig_sentiment_time(), _fig_sentiment_platform(),
        _fig_top_topics(df), _fig_emerging(), _fig_keywords(df), _fig_engagement_sentiment(),
    ]
    blocks = []
    for i, fig in enumerate(figs):
        fig.update_layout(template="plotly_white", height=420, margin=dict(t=60, l=60, r=30, b=60))
        blocks.append(fig.to_html(full_html=False, include_plotlyjs=(plotlyjs if i == 0 else False)))

    head = (
        "<h1>SocialPulse Market Intelligence - Dashboard</h1>"
        "<p>Social media analytics across YouTube and Instagram (Twitter is EDA-only). "
        "Sentiment uses the production scorer (VADER); engagement is normalized within platform. "
        "See docs/final_report.md for interpretation and recommendations.</p>"
    )
    style = ("<style>body{font-family:Segoe UI,Arial,sans-serif;margin:24px;max-width:1100px}"
             "h1{margin-bottom:4px}p{color:#444}.panel{margin:18px 0;border:1px solid #eee;border-radius:8px;padding:8px}</style>")
    body = head + "".join(f"<div class='panel'>{b}</div>" for b in blocks)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(f"<!doctype html><html><head><meta charset='utf-8'>{style}</head><body>{body}</body></html>",
                   encoding="utf-8")
    print(f"Dashboard written: {OUT} ({OUT.stat().st_size // 1024} KB, {len(figs)} panels)")


if __name__ == "__main__":
    main()
