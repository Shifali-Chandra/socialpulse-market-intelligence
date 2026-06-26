"""
SocialPulse - Topic modeling and text embeddings.

NMF on TF-IDF is the primary topic model (more coherent than LDA on short social
text); LDA is fitted at the chosen k as a comparison baseline. Number of topics is
chosen by a UMass-coherence sweep. TruncatedSVD/LSA gives dense 100-dim embeddings
(no GPU / heavy downloads). Vectorizer/model fitted on English rows, applied to all.
"""

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import NMF, LatentDirichletAllocation, TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

KEYWORDS = [
    "chatgpt", "ai", "agents", "automation", "aws", "databricks", "data",
    "engineering", "digital", "marketing", "seo", "influencer", "startup",
    "saas", "transformation",
]
# Praise / politeness / meta words dominate social comments and bury content themes;
# stoplisting them lets NMF surface what people actually discuss.
PRAISE_META = {
    "thank", "thanks", "thankyou", "thx", "great", "good", "nice", "amazing", "awesome",
    "excellent", "wonderful", "fantastic", "love", "loved", "best", "super", "perfect",
    "please", "sir", "maam", "mam", "bro", "brother", "guys", "appreciate", "appreciated",
    "helpful", "useful", "informative", "info", "information", "share", "sharing", "shared",
    "lot", "really", "video", "videos", "content", "explanation", "explained", "explain",
    "teaching", "taught", "learn", "learnt", "learned", "learning", "watch", "watching",
    "subscribe", "subscribed", "channel", "keep", "work", "job", "well", "make", "made",
    "got", "way", "things", "thing", "want", "need", "know", "going", "lot", "yes", "yeah",
}
MARKETING_STOPWORDS = sorted(
    set(KEYWORDS) | PRAISE_META | {"https", "http", "amp", "com", "www", "quot", "39"}
)


def build_vectorizer() -> TfidfVectorizer:
    stop = list(set(TfidfVectorizer(stop_words="english").get_stop_words()) | set(MARKETING_STOPWORDS))
    return TfidfVectorizer(min_df=5, max_df=0.5, ngram_range=(1, 2),
                           stop_words=stop, sublinear_tf=True, max_features=5000)


def _top_words(components: np.ndarray, feature_names: np.ndarray, n: int = 10) -> list:
    return [[feature_names[i] for i in comp.argsort()[::-1][:n]] for comp in components]


def _umass_coherence(top_word_idx: list, count_bin) -> float:
    """Mean UMass coherence over topics (higher = better)."""
    doc_freq = np.asarray((count_bin > 0).sum(axis=0)).ravel()
    cb = (count_bin > 0).astype(int)
    scores = []
    for idx in top_word_idx:
        s, pairs = 0.0, 0
        for a in range(1, len(idx)):
            for b in range(a):
                wi, wj = idx[a], idx[b]
                co = int(cb[:, wi].multiply(cb[:, wj]).sum())
                s += np.log((co + 1) / (doc_freq[wj] + 1e-12))
                pairs += 1
        if pairs:
            scores.append(s / pairs)
    return float(np.mean(scores)) if scores else float("nan")


def run(df: pd.DataFrame, text_col: str = "clean_text", lang_col: str = "lang",
        k_range=range(5, 16), out_dir: Path = Path("data/reports/model_eval"),
        models_dir: Path = Path("models"), embeddings_path: Path = Path("data/processed/embeddings.npy")):
    """Fit topics + embeddings, assign per-row topic, write sweep + terms; return (df, best_k, topic_terms)."""
    df = df.copy()
    texts_all = df[text_col].fillna("").astype(str)
    en = df[lang_col] == "en"
    texts_en = texts_all[en]

    vec = build_vectorizer()
    X_en = vec.fit_transform(texts_en)
    X_all = vec.transform(texts_all)
    feats = np.array(vec.get_feature_names_out())

    # Binary count matrix on the same vocabulary for coherence.
    # ngram_range must match the TF-IDF vectorizer or bigram terms get doc_freq 0.
    cvec = CountVectorizer(vocabulary=vec.vocabulary_, binary=True, ngram_range=(1, 2))
    count_bin = cvec.fit_transform(texts_en)

    print("Sweeping number of topics (NMF, UMass coherence):")
    sweep = []
    for k in k_range:
        nmf = NMF(n_components=k, init="nndsvd", random_state=42, max_iter=400)
        W = nmf.fit_transform(X_en)
        tw = _top_words(nmf.components_, feats)
        tw_idx = [[list(feats).index(w) for w in t] for t in tw]
        coh = _umass_coherence(tw_idx, count_bin)
        sweep.append({"k": k, "nmf_reconstruction_err": round(nmf.reconstruction_err_, 4),
                      "nmf_umass_coherence": round(coh, 4)})
        print(f"  k={k:>2}  recon_err={nmf.reconstruction_err_:.3f}  coherence={coh:.4f}")

    sweep_df = pd.DataFrame(sweep)
    out_dir.mkdir(parents=True, exist_ok=True)
    sweep_df.to_csv(out_dir / "topic_k_selection.csv", index=False, encoding="utf-8-sig")
    best_k = int(sweep_df.loc[sweep_df["nmf_umass_coherence"].idxmax(), "k"])
    print(f"Selected k={best_k} (max coherence). Sweep -> {out_dir / 'topic_k_selection.csv'}")

    # Final NMF at best_k, assign topics to ALL rows.
    nmf = NMF(n_components=best_k, init="nndsvd", random_state=42, max_iter=600)
    nmf.fit(X_en)
    W_all = nmf.transform(X_all)
    row_sums = W_all.sum(axis=1)
    has_topic = row_sums > 0
    dom = W_all.argmax(axis=1)
    dom[~has_topic] = -1  # OOV / empty / non-English rows have no topic signal
    df["dominant_topic_id"] = dom
    df["topic_weight"] = np.where(has_topic, W_all.max(axis=1) / np.where(has_topic, row_sums, 1), 0.0).round(4)

    top_words = _top_words(nmf.components_, feats)
    labels = {i: f"T{i}: " + ", ".join(words[:4]) for i, words in enumerate(top_words)}
    labels[-1] = "no_topic"
    df["dominant_topic_label"] = df["dominant_topic_id"].map(labels)
    print(f"Rows with no topic signal (no_topic): {int((~has_topic).sum())}")

    terms_rows = [{"topic_id": i, "rank": r + 1, "term": w}
                  for i, words in enumerate(top_words) for r, w in enumerate(words)]
    topic_terms = pd.DataFrame(terms_rows)
    topic_terms.to_csv(out_dir / "topic_terms.csv", index=False, encoding="utf-8-sig")

    # LDA comparison at best_k (perplexity + coherence).
    lda = LatentDirichletAllocation(n_components=best_k, random_state=42, max_iter=20, learning_method="batch")
    lda.fit(X_en)
    lda_tw = _top_words(lda.components_, feats)
    lda_idx = [[list(feats).index(w) for w in t] for t in lda_tw]
    lda_coh = _umass_coherence(lda_idx, count_bin)
    print(f"LDA comparison at k={best_k}: perplexity={lda.perplexity(X_en):.1f}  coherence={lda_coh:.4f}")

    # LSA embeddings (fit on English, transform all).
    svd = TruncatedSVD(n_components=100, random_state=42)
    svd.fit(X_en)
    emb = svd.transform(X_all).astype(np.float32)
    embeddings_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(embeddings_path, emb)
    print(f"LSA embeddings {emb.shape} -> {embeddings_path}")

    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(vec, models_dir / "tfidf_vectorizer.joblib")
    joblib.dump(nmf, models_dir / "nmf_model.joblib")

    nmf_coh = float(sweep_df["nmf_umass_coherence"].max())
    eval_rows = pd.DataFrame([
        {"model": "nmf", "family": "topic", "k": best_k, "umass_coherence": round(nmf_coh, 4), "perplexity": ""},
        {"model": "lda", "family": "topic", "k": best_k, "umass_coherence": round(lda_coh, 4),
         "perplexity": round(lda.perplexity(X_en), 1)},
    ])
    eval_rows.to_csv(out_dir / "topic_model_eval.csv", index=False, encoding="utf-8-sig")
    return df, best_k, topic_terms


def main() -> None:
    df = pd.read_csv("data/clean/unified_dataset.csv")
    sys.path.insert(0, "src")
    from text_features import add_text_features
    df = add_text_features(df)
    run(df)


if __name__ == "__main__":
    main()
