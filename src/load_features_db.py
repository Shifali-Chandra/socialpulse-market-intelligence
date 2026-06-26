"""
SocialPulse - Load the feature-rich dataset into SQLite with retrieval optimization.
Creates post_features (+ b-tree indexes), a model_eval table, a topic_terms table,
and an FTS5 full-text index over clean_text. Demonstrates index use and MATCH vs LIKE.
"""

import sqlite3
import time
from pathlib import Path

import pandas as pd

DB = Path("data/socialpulse.db")
FEATURES = Path("data/clean/features_dataset.csv")
EVAL_DIR = Path("data/reports/model_eval")

INDEXES = [
    ("idx_feat_platform", "Platform"),
    ("idx_feat_keyword", "Keyword"),
    ("idx_feat_sentiment", "sentiment_label"),
    ("idx_feat_topic", "dominant_topic_id"),
    ("idx_feat_tier", "engagement_tier"),
    ('idx_feat_date', '"Published Date"'),
    ("idx_feat_platform_keyword", "Platform, Keyword"),
]


def _load_eval() -> pd.DataFrame:
    frames = []
    for name in ["sentiment_benchmark.csv", "topic_model_eval.csv"]:
        p = EVAL_DIR / name
        if p.exists():
            df = pd.read_csv(p)
            df.insert(0, "task", "sentiment" if "sentiment" in name else "topic")
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> None:
    df = pd.read_csv(FEATURES)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    df.to_sql("post_features", conn, if_exists="replace", index=False)
    print(f"post_features: {len(df)} rows written.")

    for name, cols in INDEXES:
        cur.execute(f"DROP INDEX IF EXISTS {name}")
        cur.execute(f"CREATE INDEX {name} ON post_features({cols})")
    print(f"Created {len(INDEXES)} b-tree indexes.")

    ev = _load_eval()
    if not ev.empty:
        ev.to_sql("model_eval", conn, if_exists="replace", index=False)
        print(f"model_eval: {len(ev)} rows.")
    tt = EVAL_DIR / "topic_terms.csv"
    if tt.exists():
        pd.read_csv(tt).to_sql("topic_terms", conn, if_exists="replace", index=False)
        print("topic_terms table written.")

    # Full-text index over clean_text (FTS5, fallback FTS4).
    fts_engine = None
    for engine in ("fts5", "fts4"):
        try:
            cur.execute("DROP TABLE IF EXISTS posts_fts")
            cur.execute(f"CREATE VIRTUAL TABLE posts_fts USING {engine}(clean_text, Keyword, Platform)")
            cur.execute("INSERT INTO posts_fts(clean_text, Keyword, Platform) "
                        "SELECT clean_text, Keyword, Platform FROM post_features")
            conn.commit()
            fts_engine = engine
            break
        except sqlite3.OperationalError:
            continue
    print(f"Full-text index: {fts_engine or 'unavailable'}")

    # Optimization evidence: EXPLAIN QUERY PLAN should SEARCH USING INDEX.
    plan = cur.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM post_features WHERE Platform=? AND Keyword=?",
        ("youtube", "AWS")).fetchall()
    print("Query plan (Platform+Keyword):", "; ".join(r[-1] for r in plan))

    if fts_engine:
        # Column-qualified MATCH so both queries search ONLY clean_text (honest head-to-head);
        # report the median of several runs since the dataset is small.
        def _median_ms(sql, param, runs=7):
            times, n = [], 0
            for _ in range(runs):
                t0 = time.perf_counter()
                n = cur.execute(sql, (param,)).fetchone()[0]
                times.append((time.perf_counter() - t0) * 1000)
            return sorted(times)[runs // 2], n
        t_fts, n_fts = _median_ms("SELECT count(*) FROM posts_fts WHERE posts_fts MATCH ?", "clean_text:chatgpt")
        t_like, n_like = _median_ms("SELECT count(*) FROM post_features WHERE clean_text LIKE ?", "%chatgpt%")
        print(f"FTS MATCH 'clean_text:chatgpt': {n_fts} rows, median {t_fts:.3f} ms | "
              f"LIKE scan: {n_like} rows, median {t_like:.3f} ms (median of 7 runs)")

    conn.commit()
    conn.close()
    print(f"Done. SQLite at {DB}")


if __name__ == "__main__":
    main()
