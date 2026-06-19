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

> **Note on Reddit:** Reddit was evaluated as a source but **dropped from scope**. Reddit's API requires a data-access application that goes through a manual approval process, and that approval did not complete within the project timeline. To stay on schedule, Reddit was replaced with Instagram (via the Apify Hashtag Scraper) and a public Twitter/X dataset (Kaggle).

---

## Project Workflow

Raw Data Collection (YouTube, Instagram, Twitter)
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

docs/             # objective, business problem, methodology
notebooks/        # eda.ipynb (analysis + visuals)
research/         # keyword strategy, platform notes
src/
├── youtube_collector.py
├── instagram_collector.py
├── data_profiler.py
├── data_cleaner.py
├── build_unified_dataset.py
└── eda.py
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

### Dataset Summary

| Dataset | Records | Use |
|----------|----------|----------|
| YouTube Comments | 4,444 | analysis + modeling |
| Instagram Posts | 291 | analysis + modeling |
| Twitter Tweets (keyword-matched) | 84,212 | EDA only (AWS-biased) |
| Unified (YouTube + Instagram) | 4,735 | modeling-ready |
| Keywords Covered | 12 | |

---

## Upcoming Work

- Exploratory Data Analysis (EDA)
- Sentiment Analysis
- Trend Identification
- Engagement Analysis
- Visualization & Reporting
- Marketing Insight Generation