"""
SocialPulse - Sample a stratified gold set of English YouTube/Instagram rows for
sentiment labeling. The labeled gold set is the deploy-domain test used to choose
the production sentiment model (Twitter in-domain scores can mislead due to domain shift).
"""

from pathlib import Path

import pandas as pd

FEATURES = Path("data/clean/features_dataset.csv")
OUT = Path("data/gold/sentiment_gold.csv")
N_PER_PLATFORM = 90
SEED = 42


def main() -> None:
    df = pd.read_csv(FEATURES)
    # English only (lexicon scope), but stratify ONLY by platform - never by any
    # model's predicted label - so the gold set is an independent test.
    df = df[(df["lang"] == "en") & (df["Content"].notna())]

    parts = []
    for plat, grp in df.groupby("Platform"):
        parts.append(grp.sample(min(N_PER_PLATFORM, len(grp)), random_state=SEED))
    gold = pd.concat(parts).sample(frac=1, random_state=SEED).reset_index(drop=True)

    # No vader_pred / model hint column is written, to avoid anchoring the labeler.
    gold = gold[["post_id", "Platform", "Keyword", "Content"]].copy()
    gold["gold_label"] = ""  # to be filled: positive / neutral / negative

    OUT.parent.mkdir(parents=True, exist_ok=True)
    gold.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Gold sample: {len(gold)} rows -> {OUT}")
    print("By platform:", gold["Platform"].value_counts().to_dict())


if __name__ == "__main__":
    main()
