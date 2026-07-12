# Data Collection Methodology

## Platforms
- YouTube
- Instagram
- Twitter/X

## Data Collection Approach
Data is collected using official platform APIs, third-party scrapers, and public datasets, driven by keyword-based searches.

### Dropped Platform: Reddit
Reddit was originally planned as a source but was **removed from scope**. Reddit's data access requires submitting an API/data-use application that is subject to a manual approval process. That approval was not granted within the project's timeline, so to avoid blocking the pipeline, Reddit was replaced with **Instagram** (Apify Hashtag Scraper) and a public **Twitter/X** dataset (Kaggle).

## Categories

### Artificial Intelligence & Automation
- ChatGPT
- AI Agents
- Automation

### Cloud & Data Technologies
- AWS
- Databricks
- Data Engineering

### Digital Marketing
- Digital Marketing
- SEO
- Influencer Marketing

### Digital Business & Startups
- Startup
- SaaS
- Digital Transformation

## Data Fields

### YouTube
- Keyword
- Video ID
- Video Title
- Comment Text
- Author
- Published Date
- Like Count

### Instagram
- Keyword
- Post ID
- Caption
- Author
- Published Date
- Like Count
- Comment Count
- Post URL

### Twitter/X
- TweetID
- text
- Lang
- Likes
- RetweetCount
- Reach
- Sentiment
- Note: no reliable timestamp (only Weekday/Hour/Day fragments), so Twitter is excluded from time-series analysis

## Collection Methods

- YouTube - YouTube Data API v3; keyword search over the 12 keywords, top videos per keyword, top-level comments collected. 4,444 comments.
- Instagram - Apify Instagram Hashtag Scraper; each keyword queried as a hashtag in weekly batches. Free-tier returns one page per hashtag. 291 posts.
- Twitter/X - Static public Kaggle dataset (~100k tweets). Integrated directly rather than collected via API. The file is Windows-1252 encoded, handled by the loader's encoding fallback.

## Automated Collection (Scheduling)

YouTube and Instagram collection is automated with a scheduled GitHub Actions workflow (.github/workflows/daily-collection.yml) that runs daily. Each run collects new content, cleans it, rebuilds the unified dataset, and commits the updated data back to the repository.

Collection is incremental and new-content-only: each collector appends to its master CSV and drops duplicates on stable keys (YouTube: Video ID + Author + Comment Text; Instagram: Post ID), then stamps a Collected At date. This grows the dataset over time without duplicates and provides a time axis for trend analysis. Twitter is static and excluded from the schedule. API keys are supplied via GitHub repository Secrets.

## Cleaning and Preprocessing

A single platform-agnostic cleaner is reused across all sources:
- Robust load: UTF-8 with cp1252/latin-1 fallback, plus column-name whitespace stripping.
- Drop duplicate rows and rows missing IDs.
- Social-media text normalization on text columns: remove URLs and @mentions, strip the '#' symbol while keeping the topic word, and collapse whitespace. URL/link columns are preserved.
- Standardize dates to YYYY-MM-DD where present.

Profiling is run twice per source, on the raw data (to diagnose) and on the cleaned data (to verify), saved per platform as raw and clean profile reports.

## Twitter Handling and Bias

Twitter has no Keyword column, so a Keyword is derived by matching the 12 keywords against tweet text; unmatched tweets are dropped. Profiling revealed strong bias:
- ~99% of keyword-matched tweets are AWS (84,212 matched, 83,467 AWS).
- ChatGPT, AI Agents, and Influencer Marketing have zero matches (the dataset predates ChatGPT).
- ~92% of tweets are English.

Because of this imbalance, Twitter is used for descriptive EDA only and never for modeling. It is stored in a separate table to prevent bias from contaminating the modeling dataset.

## Unified Schema and Mapping

All sources map to a single schema: Platform, Keyword, Content, Author, Published Date, Engagement Score.

| Platform | Content | Engagement Score | Published Date |
|----------|---------|------------------|----------------|
| YouTube | Comment Text | Like Count | Published Date |
| Instagram | Caption | Like Count + Comment Count | Published Date |
| Twitter/X | text | Likes + RetweetCount | null (no reliable timestamp) |

## Storage

Outputs are written to CSV and to a SQLite database (data/socialpulse.db):
- unified_posts - YouTube + Instagram (4,735 rows), balanced and modeling-ready.
- twitter_eda - Twitter (84,212 rows), isolated for EDA only.

## Exploratory Data Analysis

EDA is performed in notebooks/eda.ipynb on the unified dataset plus the Twitter EDA set, segmented by platform to avoid pooling biased data. Outputs:
- Charts (data/reports/eda/figures): records per platform, keyword volume, Twitter AWS bias, average engagement by platform and by keyword.
- Summary tables (data/reports/eda): platform_summary, keyword_distribution, engagement_by_keyword, top_authors.

Key findings:
- YouTube and Instagram cover all 12 keywords and are balanced, so they are the analysis and modeling sources.
- Twitter is ~99% AWS, so it is used for descriptive EDA only.
- Engagement is platform-specific and is compared within a platform, not pooled across platforms.

## Feature Engineering and Modeling

The cleaned unified dataset is enriched into a feature-rich table (one row per post)
covering text, sentiment, topic, embedding, and engagement features, then stored in
SQLite with indexes and a full-text index. Summary of the approach:

- Text: language detection, a modeling-ready cleaned text, and structural counts (length, hashtags, mentions, emojis, etc.).
- Sentiment: lexicon scorers (VADER, TextBlob) and supervised TF-IDF classifiers trained on Twitter's labeled sentiment; the production model is chosen by macro-F1 on an independent YouTube/Instagram labeled set rather than the training score, because the Twitter-trained model does not transfer across domains.
- Topics: TF-IDF then NMF (primary) with LDA as a comparison; number of topics chosen by a coherence sweep.
- Embeddings: TruncatedSVD/LSA dense vectors over the TF-IDF matrix.
- Engagement: log, within-platform percentile, and tier features (never pooled across platforms).

Full feature definitions, model leaderboards, and limitations are documented in
docs/feature_engineering.md.

## Advanced Analysis (Week 5)

Time-series analysis (src/trends.py) computes sentiment share, post volume, and topic
prevalence per week, windowed to the recent dense period (older YouTube comments are
sparse). Emerging topics are flagged by comparing each topic's share in the recent half
of the window vs the earlier half. Outputs are written to data/reports/trends, and an
auto-generated factual rollup is written to data/reports/insights_summary.md (src/make_insights.py).
Model validation metrics (sentiment in-domain and deploy-domain leaderboards, topic
coherence) live in the model_eval reports. The analysis and sentiment plots are presented
in notebooks/05_analysis.ipynb; interpretation and marketing recommendations are reserved
for the final report.

## Data Processing Workflow

Collection
↓
Profiling (raw)
↓
Cleaning and Preprocessing
↓
Profiling (clean)
↓
Unified Dataset (YouTube + Instagram)  +  Twitter EDA set
↓
SQLite Storage
↓
Exploratory Analysis and Visualization
↓
Insight Generation