# Feature Engineering (Phase 2, Week 4)

This documents the feature-rich dataset, the NLP transforms, and the model selection
for SocialPulse. All modeling uses the unified YouTube + Instagram corpus
(`data/clean/unified_dataset.csv`, 4,735 rows). Twitter stays EDA-only (AWS-biased),
but its labeled `Sentiment` column is used to train and benchmark sentiment models.

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

`data/clean/features_dataset.csv` - 4,717 rows (18 empty-content rows dropped), 37 columns.

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

- **TF-IDF**: 1-2 grams, min_df=5, max_df=0.5, sublinear_tf. Two separate vectorizers are used: the **topic** vectorizer (max_features=5000, English + a marketing stoplist of the 15 keyword tokens plus "https"/"video"/etc., persisted to `models/tfidf_vectorizer.joblib`) feeds NMF/LDA; the **sentiment** classifier uses its own TF-IDF (max_features=20000, no marketing stoplist) fitted on Twitter inside the model pipeline.
- **Embeddings**: TruncatedSVD / LSA, 100 dimensions over the TF-IDF matrix, saved to `data/processed/embeddings.npy`. Chosen over transformer embeddings because there is no GPU, the corpus is small (4,717 rows, overfit risk), and the timeline is short; transformer embeddings are noted as future work.
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
**platform only** (~90 YouTube + up to 90 Instagram English rows), never by any model's
predicted label, and the labeler is shown only the text (no model-prediction hint), so it
is an independent deploy-domain test with both platforms represented. Labels are LLM-assigned.

**Deploy-domain leaderboard** (independent gold set, natural class distribution
127 pos / 36 neu / 17 neg; `data/reports/model_eval/sentiment_gold_eval.csv`):

| model | macro-F1 (gold) | accuracy |
|-------|-----------------|----------|
| textblob | 0.624 | 0.756 |
| vader | 0.572 | 0.767 |
| tfidf_supervised (linsvc) | 0.507 | 0.717 |

**Result**: the supervised classifier that won in-domain (macro-F1 0.893) drops to 0.507
on the deploy domain, while both lexicon methods hold up - the predicted domain shift
(the Twitter TF-IDF vocabulary, AWS / pre-ChatGPT, goes out-of-vocabulary on 2026
"ChatGPT / AI agents / LLM" comments). On the independent gold set **TextBlob has the
highest macro-F1 (0.624)**, with VADER a close second (0.572, marginally higher accuracy).
Per the pre-committed macro-F1 rule, **TextBlob is the production scorer for
YouTube/Instagram.** The TextBlob-vs-VADER margin is within sampling noise on 180 rows
(17 negatives), so either lexicon is defensible; the supervised model is clearly weakest
cross-domain. All lexicon scores (vader_compound, textblob_polarity/subjectivity) are
stored as features; non-English rows are labeled `undetermined` rather than guessed.

Methodology note: an earlier gold set was stratified by VADER's own predicted labels
(circular) and showed VADER ahead at 0.712. Re-sampling stratified by platform only, with
no model-prediction hint shown to the labeler, corrected this and changed the winner - a
concrete demonstration of why an independent test set matters. Labels are LLM-assigned
(no human annotators), a documented weak-supervision proxy.

## Topics (model selection)

- **NMF on TF-IDF** is primary (more coherent on short social text); **LDA** is the comparison baseline.
- **Number of topics**: swept k in {5..15} by UMass-style coherence; **k=9** selected (peak coherence).
- **NMF vs LDA at k=9**: NMF UMass coherence -1.00 vs LDA -2.78 (LDA perplexity 8379). NMF is more coherent (less-negative UMass) and is the chosen topic model. (UMass is negative by construction; less negative = more coherent.)
- **Preprocessing for topics**: HTML entities are decoded (so artifacts like `&#39;`/`&quot;` do not leak in as "39"/"quot"), and a praise/politeness/meta stoplist (thanks, great, sir, video, helpful, ...) is removed so NMF surfaces content themes (e.g. business/startup, online courses, AI agents) rather than appreciation clusters.
- Fitted globally on English rows, applied to all; per-row `dominant_topic_id` / `dominant_topic_label` / `topic_weight`. Top terms per topic in the `topic_terms` table and `data/reports/model_eval/topic_terms.csv`.
- Rows whose TF-IDF vector is all-zero (out-of-vocabulary / non-English / pure-reaction after stoplisting, 1030 rows) are assigned `dominant_topic_id = -1` (`no_topic`) and excluded from topic-prevalence reports, rather than silently defaulting to topic 0.

## Engagement features

Engagement is platform-specific and right-skewed (median 0, max 8,645), so all
normalization is **within platform**, never pooled:
- `engagement_log` = log1p(raw) to tame the tail.
- `engagement_pct_within_platform` = percentile rank within each platform (headline 0-1 metric).
- `engagement_high` = top quartile within platform.
- `engagement_tier` = none (the 71% zeros) / med / high within platform.
No virality/velocity target: collection is new-content-only, so engagement is descriptive only.

## Storage optimization

SQLite (`data/socialpulse.db`):
- `post_features` (one row per post) with 7 b-tree indexes (Platform, Keyword, sentiment_label, dominant_topic_id, engagement_tier, Published Date, and a composite Platform+Keyword).
- `model_eval` (every model's metrics, queryable) and `topic_terms`.
- `posts_fts` - an FTS5 full-text index over clean_text/Keyword/Platform.
- Evidence: `EXPLAIN QUERY PLAN` shows `SEARCH ... USING INDEX idx_feat_platform_keyword`; a column-qualified FTS `MATCH 'clean_text:chatgpt'` (79 rows) runs in ~0.04 ms vs ~2.4 ms for the equivalent `LIKE '%chatgpt%'` scan (85 rows), median of 7 runs. The dataset is small, so this is illustrative rather than operationally significant.

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
- Domain shift (Twitter AWS/pre-ChatGPT -> 2026 YT/IG AI) means the Twitter-trained model may not transfer; the gold set is the honest mitigation.
- The Twitter `Sentiment` zero-mass (67%) may be "unscored" rather than truly neutral; treated as a documented assumption.
- Instagram n=291 (~24/keyword) is too small for per-keyword conclusions; reported as directional with row counts.
- Multilingual rows (~28% non-English) are scored `undetermined` and excluded from English-only topic fitting.
- Coherence is a relative UMass-style proxy (no gensim); used for model/k comparison, not as an absolute score.
- YouTube comments are heavily appreciation/reaction text ("thanks, great video"), so even after stoplisting ~1030 rows carry no content theme (no_topic) and some topics remain reaction-flavored. The richer content signal lives in video titles and Instagram captions; modeling topics on titles/captions (and assigning each comment its video's topic) is the recommended next enhancement for sharper "emerging topics".
