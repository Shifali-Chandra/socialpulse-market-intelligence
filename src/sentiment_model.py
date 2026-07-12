"""
SocialPulse - Sentiment scoring and model benchmark.

Lexicon scorers (VADER, TextBlob) plus supervised TF-IDF classifiers trained on
Twitter's labeled Sentiment. `--benchmark` evaluates every model on a held-out
Twitter test set (macro-F1 primary, since 67% of labels are neutral) and writes a
leaderboard. VADER is the production scorer for YouTube/Instagram unless a model
beats it on the deploy-domain gold set (see sentiment_gold).
"""

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_VADER = SentimentIntensityAnalyzer()
POS, NEU, NEG = "positive", "neutral", "negative"


def label_from_compound(c: float) -> str:
    """Map a [-1, 1] polarity score to a 3-class label (standard +/-0.05 band)."""
    if c >= 0.05:
        return POS
    if c <= -0.05:
        return NEG
    return NEU


def twitter_float_to_class(s: pd.Series) -> pd.Series:
    """Twitter continuous Sentiment -> classes: <0 neg, ==0 neu, >0 pos."""
    return s.apply(lambda v: NEG if v < 0 else (POS if v > 0 else NEU))


def add_lexicon_sentiment(
    df: pd.DataFrame, text_col: str = "clean_text_cased", lang_col: str = "lang"
) -> pd.DataFrame:
    """Add VADER + TextBlob scores and a VADER-based sentiment label/score.

    Scores case-preserved text (clean_text_cased), since VADER uses capitalization
    and emphasis; lowercasing loses signal.
    """
    df = df.copy()
    texts = df[text_col].fillna("").astype(str)
    df["vader_compound"] = texts.apply(lambda t: _VADER.polarity_scores(t)["compound"])
    tb = texts.apply(lambda t: TextBlob(t).sentiment)
    df["textblob_polarity"] = tb.apply(lambda s: round(s.polarity, 4))
    df["textblob_subjectivity"] = tb.apply(lambda s: round(s.subjectivity, 4))

    # Production scorer = VADER: it wins macro-F1 on the independent YouTube/Instagram
    # gold set (see sentiment_gold_eval). TextBlob scores are kept as features for comparison.
    is_en = df[lang_col] == "en"
    df["sentiment_label"] = "undetermined"
    df.loc[is_en, "sentiment_label"] = df.loc[is_en, "vader_compound"].apply(label_from_compound)
    df["sentiment_score"] = df["vader_compound"].where(is_en)
    df["sentiment_model"] = "vader"
    return df


def _load_twitter_training(path: Path) -> tuple:
    df = pd.read_csv(path)
    df = df[df["Lang"] == "en"].dropna(subset=["text", "Sentiment"])
    X = df["text"].astype(str)
    y = twitter_float_to_class(df["Sentiment"])
    return X, y


def _evaluate(name, family, y_true, y_pred, rows):
    macro = f1_score(y_true, y_pred, average="macro", labels=[NEG, NEU, POS])
    rep = classification_report(y_true, y_pred, labels=[NEG, NEU, POS], output_dict=True, zero_division=0)
    rows.append({
        "model": name, "family": family, "dataset": "twitter_test",
        "macro_f1": round(macro, 4), "accuracy": round(rep["accuracy"], 4),
        "f1_negative": round(rep[NEG]["f1-score"], 4),
        "f1_neutral": round(rep[NEU]["f1-score"], 4),
        "f1_positive": round(rep[POS]["f1-score"], 4),
    })
    print(f"  {name:<28} macro-F1={macro:.4f}  acc={rep['accuracy']:.4f}")
    return macro


def benchmark(twitter_path: Path, out_dir: Path, models_dir: Path) -> None:
    print("Loading Twitter labeled data...")
    X, y = _load_twitter_training(twitter_path)
    print(f"English labeled tweets: {len(X)} | class balance: {y.value_counts(normalize=True).round(3).to_dict()}")
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    rows = []
    print("Evaluating models on held-out Twitter test set (macro-F1 primary):")

    dummy = DummyClassifier(strategy="most_frequent").fit(X_tr.values.reshape(-1, 1), y_tr)
    _evaluate("majority_baseline", "baseline", y_te, dummy.predict(X_te.values.reshape(-1, 1)), rows)
    _evaluate("vader", "lexicon", y_te, [label_from_compound(_VADER.polarity_scores(t)["compound"]) for t in X_te], rows)
    _evaluate("textblob", "lexicon", y_te, [label_from_compound(TextBlob(t).sentiment.polarity) for t in X_te], rows)

    def tfidf():
        return TfidfVectorizer(min_df=5, max_df=0.5, ngram_range=(1, 2), sublinear_tf=True, max_features=20000)

    supervised = {
        "tfidf_nb": Pipeline([("tfidf", tfidf()), ("clf", MultinomialNB())]),
        "tfidf_logreg": Pipeline([("tfidf", tfidf()), ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))]),
        "tfidf_linsvc": Pipeline([("tfidf", tfidf()), ("clf", LinearSVC(class_weight="balanced"))]),
    }
    best_name, best_macro, best_pipe = None, -1, None
    for name, pipe in supervised.items():
        pipe.fit(X_tr, y_tr)
        macro = _evaluate(name, "supervised", y_te, pipe.predict(X_te), rows)
        if macro > best_macro:
            best_name, best_macro, best_pipe = name, macro, pipe

    out_dir.mkdir(parents=True, exist_ok=True)
    board = pd.DataFrame(rows).sort_values("macro_f1", ascending=False)
    board.to_csv(out_dir / "sentiment_benchmark.csv", index=False, encoding="utf-8-sig")
    print(f"\nLeaderboard written: {out_dir / 'sentiment_benchmark.csv'}")
    print(board.to_string(index=False))

    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_pipe, models_dir / "sentiment_best.joblib")
    print(f"\nBest supervised model ({best_name}, macro-F1={best_macro:.4f}) saved to models/sentiment_best.joblib")
    print("Production scorer for YouTube/Instagram: VADER (deploy-domain choice; see docs/feature_engineering.md).")


def main() -> None:
    p = argparse.ArgumentParser(description="Sentiment scoring and model benchmark.")
    p.add_argument("--benchmark", action="store_true", help="Train and benchmark on Twitter labels")
    p.add_argument("--twitter", type=Path, default=Path("data/clean/twitter_cleaned.csv"))
    p.add_argument("--out-dir", type=Path, default=Path("data/reports/model_eval"))
    p.add_argument("--models-dir", type=Path, default=Path("models"))
    args = p.parse_args()
    if args.benchmark:
        benchmark(args.twitter, args.out_dir, args.models_dir)
    else:
        print("Nothing to do. Use --benchmark, or import add_lexicon_sentiment for scoring.")


if __name__ == "__main__":
    main()
