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