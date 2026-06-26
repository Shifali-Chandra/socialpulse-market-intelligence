"""
SocialPulse - Evaluate sentiment models on the hand/LLM-labeled YouTube/Instagram
gold set (the real deploy domain) and pick the production scorer. Twitter in-domain
scores can mislead due to domain shift; this gold macro-F1 is the deciding metric.
"""

import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import f1_score

sys.path.insert(0, "src")
from sentiment_model import label_from_compound, _VADER, POS, NEU, NEG
from data_cleaner import _clean_social_text
from textblob import TextBlob

GOLD = Path("data/gold/sentiment_gold.csv")
OUT = Path("data/reports/model_eval/sentiment_gold_eval.csv")
MODEL = Path("models/sentiment_best.joblib")
LABELS = [NEG, NEU, POS]


def main() -> None:
    g = pd.read_csv(GOLD)
    g = g[g["gold_label"].isin(LABELS)].copy()
    if g.empty:
        print("No gold labels found. Fill gold_label first.")
        return
    print(f"Gold rows labeled: {len(g)} | dist: {g['gold_label'].value_counts().to_dict()}")

    # Lexicon models score case-preserved cleaned text (their production input);
    # the supervised model scores raw Content (train/serve-consistent with Twitter).
    clean = g["Content"].fillna("").astype(str).apply(_clean_social_text)
    preds = {
        "vader": clean.apply(lambda t: label_from_compound(_VADER.polarity_scores(t)["compound"])),
        "textblob": clean.apply(lambda t: label_from_compound(TextBlob(t).sentiment.polarity)),
    }
    if MODEL.exists():
        preds["tfidf_supervised"] = pd.Series(joblib.load(MODEL).predict(g["Content"].fillna("").astype(str)), index=g.index)

    rows = []
    for name, p in preds.items():
        macro = f1_score(g["gold_label"], p, average="macro", labels=LABELS)
        acc = (p.values == g["gold_label"].values).mean()
        rows.append({"model": name, "dataset": "yt_ig_gold", "macro_f1": round(macro, 4), "accuracy": round(acc, 4)})
    board = pd.DataFrame(rows).sort_values("macro_f1", ascending=False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    board.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(board.to_string(index=False))
    best = board.iloc[0]
    print(f"\nPRODUCTION sentiment model (by deploy-domain gold macro-F1): {best['model']} "
          f"(macro-F1={best['macro_f1']})")


if __name__ == "__main__":
    main()
