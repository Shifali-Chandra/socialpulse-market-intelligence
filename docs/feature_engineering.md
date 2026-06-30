# Feature Engineering (Phase 2, Week 4)

This documents the feature-rich dataset, the NLP transforms, and the model selection
for SocialPulse. Numbers below reflect the refreshed run on the full collected dataset
(~14.3k posts; the corpus grows daily via the scheduled collection). All modeling uses
the unified YouTube + Instagram corpus (`data/clean/unified_dataset.csv`). Twitter stays
EDA-only (AWS-biased), but its labeled `Sentiment` column is used to train and benchmark
sentiment models.

## Pipeline

```
unified_dataset.csv
  -> text_features.py        language detection, clean_text, structural counts
  -> sentiment_model.py      VADER/TextBlob scores + Twitter-trained classifiers
  -> topic_model.py          TF-IDF -> NMF/LDA topics + LSA embeddings
  -> engagement_features.py  within-platform log / percentile / tier
  -> build_features.py       assembles features_dataset.csv (one row per post)
  -> load_features_db.py     SQLite post_features + indexes + FTS5
  -> make_feature_reports.py marketing summary tables
```

## Feature-rich dataset

`data/clean/features_dataset.csv` - 14,313 rows (64 empty-content rows dropped), 37 columns.

| Group | Columns |
|-------|---------|
| Identity | post_id, Platform, Keyword, Author, Published Date, Content, clean_text |
| Language | lang (langdetect), sentiment_reliable (lang == en) |
| Structural | char_len, word_count, avg_word_len, hashtag_count, mention_count, url_count, emoji_count, uppercase_ratio, exclaim_count, question_count |
| Sentiment | vader_compound, textblob_polarity, textblob_subjectivity, sentiment_label, sentiment_score, sentiment_model |
| Topic | dominant_topic_id, dominant_topic_label, topic_weight |
| Engagement | engagement_raw, engagement_log, engagement_pct_within_platform, engagement_high, engagement_tier |
| Time | pub_year, pub_month, pub_dayofweek, pub_is_weekend |

## NLP transforms

- **TF-IDF**: 1-2 grams, min_df=5, max_df=0.5, sublinear_tf. Two separate vectorizers: the **topic** vectorizer (max_features=5000, English + a marketing stoplist of the 15 keyword tokens plus praise/politeness/meta words, persisted to `models/tfidf_vectorizer.joblib`) feeds NMF/LDA; the **sentiment** classifier uses its own TF-IDF (max_features=20000, no marketing stoplist) fitted on Twitter inside the model pipeline.
- **Embeddings**: TruncatedSVD / LSA, 100 dimensions over the TF-IDF matrix, saved to `data/processed/embeddings.npy`. Chosen over transformer embeddings because there is no GPU, the timeline is short, and overfit risk on this corpus; transformer embeddings (e.g. sentence-transformers) are noted as a future upgrade.
- The vectorizer and models are fitted on English rows (`lang == en`) and applied to all rows, to avoid multilingual contamination.

## Sentiment (model selection)

**Label scheme**: Twitter's continuous `Sentiment` (-6 to +7.33) is collapsed to 3 classes: `<0` negative, `==0` neutral, `>0` positive. The 100k-row prior is neg 5.6% / neu 67.4% / pos 27.0% - heavily imbalanced, so macro-F1 (not accuracy) is the primary metric and supervised models use `class_weight='balanced'`. VADER/TextBlob compound scores map to the same 3 classes via the standard +/-0.05 band.

**In-domain benchmark** (held-out 20% of 91,886 English tweets):

| model | macro-F1 | accuracy |
|-------|----------|----------|
| tfidf_linsvc | 0.893 | 0.946 |
| tfidf_logreg | 0.850 | 0.921 |
| tfidf_nb | 0.779 | 0.873 |
| vader | 0.680 | 0.711 |
| textblob | 0.511 | 0.623 |
| majority baseline | 0.267 | 0.668 |

**Deploy-domain selection**: in-domain Twitter scores can mislead, because the deploy
domain (2026 YouTube/Instagram AI content) differs sharply from the training domain
(pre-ChatGPT, 99% AWS tweets) - the supervised TF-IDF vocabulary goes largely
out-of-vocabulary on terms like "ChatGPT", "agents", "LLM". A YouTube/Instagram gold set
(`data/gold/sentiment_gold.csv`) is the deciding test. It is sampled stratified by
**platform only** (90 YouTube + 90 Instagram English rows), never by any model's predicted
label, and the labeler is shown only the text (no model-prediction hint), so it is an
independent deploy-domain test with both platforms represented. Labels are LLM-assigned.

**Deploy-domain leaderboard** (independent gold set, 178 labeled rows, natural class
distribution 112 pos / 36 neu / 30 neg; `data/reports/model_eval/sentiment_gold_eval.csv`):

| model | macro-F1 (gold) | accuracy |
|-------|-----------------|----------|
| vader | 0.649 | 0.758 |
| textblob | 0.528 | 0.685 |
| tfidf_supervised (linsvc) | 0.522 | 0.646 |

**Result**: the supervised classifier that won in-domain (macro-F1 0.893) drops to 0.522
on the deploy domain - the predicted domain shift (the Twitter TF-IDF vocabulary, AWS /
pre-ChatGPT, goes out-of-vocabulary on 2026 "ChatGPT / AI agents / LLM" comments). The
two lexicon scorers both beat it; **VADER has the highest deploy-domain macro-F1 (0.649)**
and is the **production scorer for YouTube/Instagram**. VADER and TextBlob are close and
the winner is sensitive to the gold sample (on an earlier, smaller sample TextBlob edged
ahead), but VADER wins on the largest/most-recent independent set and the supervised model
is consistently the weakest cross-domain. All lexicon scores (vader_compound,
textblob_polarity/subjectivity) are stored as features; non-English rows are labeled
`undetermined` rather than guessed. Labels are LLM-assigned (no human annotators), a
documented weak-supervision proxy.

## Topics (model selection)

- **NMF on TF-IDF** is primary (more coherent on short social text); **LDA** is the comparison baseline.
- **Number of topics**: swept k in {5..15} by UMass-style coherence; **k=11** selected (peak coherence).
- **NMF vs LDA at k=11**: NMF UMass coherence -1.83 vs LDA -2.92 (LDA perplexity 14851). NMF is more coherent (less-negative UMass) and is the chosen topic model. (UMass is negative by construction; less negative = more coherent.)
- **Preprocessing for topics**: HTML entities are decoded (so artifacts like `&#39;`/`&quot;` do not leak in as "39"/"quot"), and a praise/politeness/meta stoplist (thanks, great, sir, video, helpful, ...) is removed so NMF surfaces content themes (business/startup, online courses, AI agents, ChatGPT usage) rather than appreciation clusters.
- Fitted globally on English rows, applied to all; per-row `dominant_topic_id` / `dominant_topic_label` / `topic_weight`. Top terms per topic in the `topic_terms` table and `data/reports/model_eval/topic_terms.csv`.
- Rows whose TF-IDF vector is all-zero (out-of-vocabulary / non-English / pure-reaction after stoplisting, 2,244 rows) are assigned `dominant_topic_id = -1` (`no_topic`) and excluded from topic-prevalence reports, rather than silently defaulting to topic 0.

## Engagement features

Engagement is platform-specific and right-skewed, so all normalization is **within
platform**, never pooled:
- `engagement_log` = log1p(raw) to tame the tail.
- `engagement_pct_within_platform` = percentile rank within each platform (headline 0-1 metric).
- `engagement_high` = top quartile within platform.
- `engagement_tier` = none (the majority zeros) / med / high within platform.
No virality/velocity target: collection is new-content-only, so engagement is descriptive only.

## Storage optimization

SQLite (`data/socialpulse.db`):
- `post_features` (one row per post) with 7 b-tree indexes (Platform, Keyword, sentiment_label, dominant_topic_id, engagement_tier, Published Date, and a composite Platform+Keyword).
- `model_eval` (every model's metrics, queryable) and `topic_terms`.
- `posts_fts` - an FTS5 full-text index over clean_text/Keyword/Platform.
- Evidence: `EXPLAIN QUERY PLAN` shows `SEARCH ... USING INDEX idx_feat_platform_keyword`; a column-qualified FTS `MATCH 'clean_text:chatgpt'` (444 rows) runs in ~0.08 ms vs ~8.4 ms for the equivalent `LIKE '%chatgpt%'` scan (450 rows), median of 7 runs - the index/full-text advantage widens as the dataset grows.

## Topic.pdf Week 4 coverage

| Requirement | Status |
|-------------|--------|
| Sentiment scores | VADER/TextBlob + supervised; per-row label and score |
| Topic distributions | NMF (primary) + LDA, per-row dominant topic + weight |
| Engagement metrics | log / within-platform percentile / tier |
| NLP transforms (TF-IDF, embeddings) | TF-IDF + LSA 100-dim embeddings |
| Storage optimization | SQLite indexes + FTS5, with timing evidence |
| Feature-rich dataset + documentation | features_dataset.csv + this document |
| Models with performance evaluations | sentiment leaderboard + topic coherence, in model_eval |

## Limitations

- Negative class is only 5.6% of Twitter labels - supervised negative recall is weak; class_weight helps but cannot manufacture signal.
- Domain shift (Twitter AWS/pre-ChatGPT -> 2026 YT/IG AI) means the Twitter-trained model does not transfer; the gold set is the honest mitigation.
- The Twitter `Sentiment` zero-mass (67%) may be "unscored" rather than truly neutral; treated as a documented assumption.
- Instagram is still small relative to YouTube, so per-keyword Instagram conclusions are directional, reported with row counts.
- Multilingual rows (~21% non-English) are scored `undetermined` and excluded from English-only topic fitting.
- Coherence is a relative UMass-style proxy (no gensim); used for model/k comparison, not as an absolute score.
- YouTube comments are heavily appreciation/reaction text, so even after stoplisting ~2,244 rows carry no content theme (no_topic) and some topics remain reaction-flavored. The richer content signal lives in video titles and Instagram captions; modeling topics on titles/captions is the recommended next enhancement for sharper "emerging topics".
