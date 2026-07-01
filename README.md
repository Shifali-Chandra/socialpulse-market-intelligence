# SocialPulse Market Intelligence

## Overview

SocialPulse Market Intelligence is a social media analytics solution designed to collect, process, and analyze public social media discussions to identify emerging trends, audience sentiment, engagement patterns, and potential business opportunities.

The project focuses on technology and digital-business related discussions across platforms such as YouTube, Instagram, and Twitter/X, helping marketing teams make data-driven marketing and business development decisions.

---

## Project Objective

Collect, validate, clean, and analyze social media data from YouTube, Instagram, and Twitter/X to generate actionable marketing insights through trend analysis, sentiment analysis, and engagement analysis.

---

## Focus Areas

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

---

## Technologies

- Python
- YouTube Data API v3
- Apify Instagram Hashtag Scraper
- Twitter/X (public Kaggle dataset)
- Pandas
- scikit-learn (TF-IDF, NMF/LDA, classifiers, LSA)
- NLTK / VADER / TextBlob (sentiment), langdetect
- SQLite (with FTS5 full-text search)
- Matplotlib, Seaborn, WordCloud
- Jupyter Notebook
- Git & GitHub
- GitHub Actions (scheduled daily collection)

> **Note on Reddit:** Reddit was evaluated as a source but **dropped from scope**. Reddit's API requires a data-access application that goes through a manual approval process, and that approval did not complete within the project timeline. To stay on schedule, Reddit was replaced with Instagram (via the Apify Hashtag Scraper) and a public Twitter/X dataset (Kaggle).

---

## Setup

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m ipykernel install --user --name socialpulse --display-name "Python (SocialPulse)"
```

API keys (YouTube `API_KEY`, Apify `APIFY_API_KEY`) go in a local `.env` file (gitignored). Pipeline scripts run from the project root, e.g. `python src/data_cleaner.py data/raw/youtube_master_dataset.csv`. Open `notebooks/eda.ipynb` with the "Python (SocialPulse)" kernel.

---

## Automation

Three GitHub Actions workflows:

- **daily-collection.yml** (daily): collects new YouTube + Instagram content, cleans it, rebuilds the unified dataset, and commits the updated data. Collection is incremental and deduplicated (new-content-only), so the dataset grows without duplicates. Twitter is static and not scheduled. Reads `API_KEY` and `APIFY_API_KEY` from GitHub repository Secrets.
- **feature-refresh.yml** (weekly + manual): re-runs feature engineering, feature reports, trend analysis, and the insights summary on the current data and commits them.
- **dashboard-refresh.yml** (manual only): on demand (Actions -> Run workflow), rebuilds features, analysis, and the interactive dashboard on the current data and commits a refreshed dashboard. It uses `build_dashboard.py --cdn` for a small committed HTML; the default local build embeds Plotly.js for offline viewing.

---

## Project Workflow

Automated Daily Collection - YouTube + Instagram (GitHub Actions, incremental + deduped); Twitter static
↓
Profiling (raw)
↓
Data Cleaning & Preprocessing
↓
Profiling (clean)
↓
Unified Dataset (YouTube + Instagram)  +  Twitter EDA set (kept separate)
↓
SQLite Storage
↓
Exploratory Data Analysis & Visualization
↓
Feature Engineering (sentiment, topics, embeddings, engagement)
↓
Trend Analysis & Dashboard (next phase)
↓
Marketing Insights

---

## Repository Structure

```
data/
├── raw/          # source datasets (youtube, instagram, twitter)
├── clean/        # cleaned per-platform + unified + features dataset
├── gold/         # labeled sentiment gold set (model validation)
├── reports/      # profiling, model_eval, feature reports, trends, insights_summary.md, dashboard.html, eda outputs
└── socialpulse.db  # SQLite (gitignored, regenerable from CSVs)

.github/workflows/  # daily-collection.yml (daily), feature-refresh.yml (weekly), dashboard-refresh.yml (manual)
docs/             # methodology, feature engineering, final report, AI-tool usage
notebooks/        # eda.ipynb, 04_feature_engineering.ipynb, 05_analysis.ipynb
src/
├── youtube_collector.py
├── instagram_collector.py
├── collector_utils.py        # incremental append + dedupe
├── data_profiler.py
├── data_cleaner.py
├── build_unified_dataset.py
├── text_features.py          # language, clean text, structural counts
├── sentiment_model.py        # lexicon + supervised sentiment + benchmark
├── topic_model.py            # TF-IDF -> NMF/LDA topics + LSA embeddings
├── engagement_features.py    # within-platform engagement transforms
├── build_features.py         # feature-engineering orchestrator
├── load_features_db.py       # SQLite feature store + indexes + FTS5
├── make_feature_reports.py   # marketing summary reports
├── trends.py                 # time-series trend analysis (Week 5)
├── make_insights.py          # auto-generated key-findings summary
└── build_dashboard.py        # interactive Plotly dashboard (Week 6)
```

---

## Current Progress

**Status (all 6 weeks delivered):** data collection, automated daily pipeline, SQLite storage, feature engineering, sentiment/topic models, advanced time-series analysis, the interactive dashboard, and the final report are complete on the full ~14,300-post corpus (production sentiment scorer: VADER). Optional enhancements (semantic embeddings, title/caption-based topics, network analysis) remain as future work.

### Completed

- Project planning and objective definition
- Keyword strategy definition (12 keywords, 4 categories)
- YouTube API integration and collection
- Instagram collection via Apify Hashtag Scraper
- Twitter/X dataset integration (Kaggle)
- Platform-agnostic profiling module with raw and clean reports
- Data cleaning module with social-media text normalization
- Robust loader (encoding fallback, column-name normalization)
- Twitter keyword derivation and EDA-only scoping (AWS bias)
- Unified dataset builder (cross-platform schema)
- SQLite integration (unified_posts + twitter_eda tables)
- Exploratory data analysis notebook (audience interests, engagement patterns, Twitter bias visualization)
- Reproducible environment (.venv + Jupyter kernel)
- Incremental, deduplicated collection (append, not overwrite)
- Automated daily collection pipeline (GitHub Actions, scheduled)
- Feature engineering pipeline (37-column feature-rich dataset)
- Sentiment scoring + model benchmark (lexicon vs supervised), production model selected on a labeled gold set
- Topic modeling (NMF/LDA, coherence-selected) + TF-IDF/LSA embeddings
- Within-platform engagement features
- SQLite feature store with b-tree indexes + FTS5 full-text search
- Feature engineering documentation ([docs/feature_engineering.md](docs/feature_engineering.md))
- Time-series trend analysis (sentiment, volume, and topics over time)
- Emerging-topic detection and top-influencer analysis
- Auto-generated key-findings summary (insights_summary.md)
- Week 5 analysis notebook with sentiment plots and validation metrics
- Interactive dashboard ([data/reports/dashboard.html](data/reports/dashboard.html), Plotly)
- Final marketing-insights report ([docs/final_report.md](docs/final_report.md)) and AI-tool-usage notes ([docs/ai_tool_usage.md](docs/ai_tool_usage.md))

### Dataset Summary

YouTube and Instagram grow daily via the scheduled collection; the counts below are a snapshot.

| Dataset | Records (snapshot) | Use |
|----------|----------|----------|
| YouTube Comments | ~12,400 (growing daily) | analysis + modeling |
| Instagram Posts | ~1,900 (growing daily) | analysis + modeling |
| Twitter Tweets (keyword-matched) | 84,212 (static) | EDA only (AWS-biased) |
| Unified / Feature dataset | ~14,300 (growing daily) | modeling-ready |
| Keywords Covered | 12 | |

---

## Future Enhancements (optional)

- Semantic (sentence-transformer) embeddings to replace LSA
- Title/caption-based topic modeling for sharper emerging-topic themes
- Comment-graph network analysis of user interactions