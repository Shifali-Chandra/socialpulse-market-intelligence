"""
SocialPulse Market Intelligence - Unified Dataset Builder
Maps each cleaned platform dataset to a single cross-platform schema:
Platform, Keyword, Content, Author, Published Date, Engagement Score.
"""

import argparse
import io
import logging
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

UNIFIED_COLUMNS = ["Platform", "Keyword", "Content", "Author", "Published Date", "Engagement Score"]

KEYWORDS = [
    "ChatGPT", "AI Agents", "Automation", "AWS",
    "Databricks", "Data Engineering", "Digital Marketing",
    "SEO", "Influencer Marketing", "Startup", "SaaS",
    "Digital Transformation",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the unified cross-platform dataset.")
    parser.add_argument("--clean-dir", type=Path, default=Path("data/clean"))
    parser.add_argument("--output", type=Path, default=Path("data/clean/unified_dataset.csv"))
    parser.add_argument("--twitter-output", type=Path, default=Path("data/clean/twitter_eda.csv"))
    parser.add_argument("--sqlite", type=Path, default=Path("data/socialpulse.db"))
    parser.add_argument("--table", default="unified_posts")
    parser.add_argument("--twitter-table", default="twitter_eda")
    return parser.parse_args()


def _read(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        logger.warning("Skipping (not found): %s", path)
        return None
    df = pd.read_csv(path)
    logger.info("Loaded %s (rows=%d)", path.name, len(df))
    return df


def _frame(platform, keyword, content, author, date, engagement) -> pd.DataFrame:
    return pd.DataFrame({
        "Platform": platform,
        "Keyword": keyword,
        "Content": content,
        "Author": author,
        "Published Date": date,
        "Engagement Score": pd.to_numeric(engagement, errors="coerce").fillna(0),
    })


def map_youtube(df: pd.DataFrame) -> pd.DataFrame:
    return _frame("youtube", df["Keyword"], df["Comment Text"], df["Author"],
                  df["Published Date"], df["Like Count"])


def map_instagram(df: pd.DataFrame) -> pd.DataFrame:
    engagement = pd.to_numeric(df["Like Count"], errors="coerce").fillna(0) + \
                 pd.to_numeric(df["Comment Count"], errors="coerce").fillna(0)
    return _frame("instagram", df["Keyword"], df["Caption"], df["Author"],
                  df["Published Date"], engagement)


def _derive_keyword(text: str):
    for k in KEYWORDS:
        if re.search(r"\b" + re.escape(k) + r"\b", str(text), re.IGNORECASE):
            return k
    return None


def map_twitter(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_kw"] = df["text"].apply(_derive_keyword)
    matched = df[df["_kw"].notna()]
    dropped = len(df) - len(matched)
    logger.info("Twitter: kept %d keyword-matched rows, dropped %d off-topic.", len(matched), dropped)
    engagement = pd.to_numeric(matched["Likes"], errors="coerce").fillna(0) + \
                 pd.to_numeric(matched["RetweetCount"], errors="coerce").fillna(0)
    return _frame("twitter", matched["_kw"], matched["text"], matched["UserID"],
                  pd.NA, engagement)


def build_from(clean_dir: Path, sources: list) -> pd.DataFrame | None:
    frames = []
    for filename, mapper in sources:
        df = _read(clean_dir / filename)
        if df is not None:
            frames.append(mapper(df))
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)[UNIFIED_COLUMNS]


def save_sqlite(df: pd.DataFrame, db_path: Path, table: str) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        df.to_sql(table, conn, if_exists="replace", index=False)
        logger.info("Wrote %d rows to SQLite %s (table: %s).", len(df), db_path, table)
    finally:
        conn.close()


def _save(df: pd.DataFrame, csv_path: Path, db_path: Path, table: str) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logger.info("CSV saved: %s", csv_path)
    save_sqlite(df, db_path, table)


def main() -> None:
    args = parse_args()

    # Modeling-ready pool: balanced, on-topic platforms only.
    unified = build_from(args.clean_dir, [
        ("youtube_cleaned.csv", map_youtube),
        ("instagram_cleaned.csv", map_instagram),
    ])
    # Twitter kept separate (AWS-biased, EDA-only) to avoid contaminating modeling.
    twitter = build_from(args.clean_dir, [("twitter_cleaned.csv", map_twitter)])

    if unified is None and twitter is None:
        logger.error("No cleaned datasets found in %s", args.clean_dir)
        sys.exit(1)

    if unified is not None:
        _save(unified, args.output, args.sqlite, args.table)
        logger.info("unified_posts per-platform counts:\n%s",
                    unified["Platform"].value_counts().to_string())
    if twitter is not None:
        _save(twitter, args.twitter_output, args.sqlite, args.twitter_table)
        logger.info("twitter_eda rows: %d", len(twitter))


if __name__ == "__main__":
    main()
