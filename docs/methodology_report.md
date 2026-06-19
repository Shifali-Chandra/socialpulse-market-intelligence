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
- (no reliable timestamp — excluded from time-series analysis)

## Data Processing Workflow

Data Collection
↓
Data Profiling
↓
Data Cleaning
↓
Exploratory Analysis
↓
Insight Generation