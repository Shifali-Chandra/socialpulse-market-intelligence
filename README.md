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
- SQLite
- Matplotlib, Seaborn
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

A scheduled GitHub Actions workflow (`.github/workflows/daily-collection.yml`) runs daily: it collects new YouTube + Instagram content, cleans it, rebuilds the unified dataset, and commits the updated data back to the repo. Collection is incremental and deduplicated (new-content-only), so the dataset grows over time without duplicates. Twitter is static and not part of the schedule. The workflow reads `API_KEY` and `APIFY_API_KEY` from GitHub repository Secrets.

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
Sentiment Analysis (next phase)
↓
Marketing Insights

---

## Repository Structure

```
data/
├── raw/          # source datasets (youtube, instagram, twitter)
├── clean/        # cleaned per-platform + unified datasets
├── reports/      # profiling reports (raw/clean) + eda outputs
└── socialpulse.db  # SQLite (gitignored, regenerable from CSVs)

.github/workflows/  # daily-collection.yml (scheduled GitHub Actions pipeline)
docs/             # methodology report
notebooks/        # eda.ipynb (analysis + visuals)
src/
├── youtube_collector.py
├── instagram_collector.py
├── collector_utils.py      # incremental append + dedupe
├── data_profiler.py
├── data_cleaner.py
└── build_unified_dataset.py
```

---

## Current Progress

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

### Dataset Summary

YouTube and Instagram grow daily via the scheduled collection; the counts below are a snapshot.

| Dataset | Records (snapshot) | Use |
|----------|----------|----------|
| YouTube Comments | ~7,200 (growing daily) | analysis + modeling |
| Instagram Posts | ~560 (growing daily) | analysis + modeling |
| Twitter Tweets (keyword-matched) | 84,212 (static) | EDA only (AWS-biased) |
| Unified (YouTube + Instagram) | growing daily | modeling-ready |
| Keywords Covered | 12 | |

---

## Upcoming Work

- Sentiment Analysis (model-based for YouTube/Instagram; Twitter has a pre-computed score)
- Topic Modeling
- Trend Identification
- Visualization expansion (word clouds, dashboard)
- Marketing Insight Generation