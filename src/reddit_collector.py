"""
SocialPulse Market Intelligence - Reddit Collector

Still in progress due to Reddit API registration delay. 
This module will fetch top posts from specified subreddits and compile them into a master dataset for analysis.
"""

import time
from pathlib import Path

from dotenv import load_dotenv
import pandas as pd
import os

load_dotenv()

# API credentials — still in process due to registration delay
# REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
# REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
# REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "socialpulse-market-intelligence/1.0")
CLIENT_ID = None
CLIENT_SECRET = None
USER_AGENT = None

SUBREDDITS = [
    "ChatGPT", "ArtificialIntelligence", "automation", "aws",
    "databricks", "dataengineering", "digitalmarketing", "SEO",
    "influencermarketing", "startups", "SaaS", "digitaltransformation",
]

OUTPUT_FILE = Path("data/raw/reddit_master_dataset.csv")

COLUMNS = [
    "Post ID",
    "Title",
    "Post Text",
    "Author",
    "Created Date",
    "Upvotes/Score",
    "Comment Count",
    "Subreddit",
]


def get_reddit_client():
    """Initialize and return a PRAW Reddit instance."""
    # import praw
    # return praw.Reddit(
    #     client_id=CLIENT_ID,
    #     client_secret=CLIENT_SECRET,
    #     user_agent=USER_AGENT,
    # )
    raise NotImplementedError("Reddit API credentials not yet registered")


def fetch_posts(reddit, subreddit_name, limit=50):
    """Fetch top posts from a subreddit (monthly filter)."""
    # subreddit = reddit.subreddit(subreddit_name)
    # return subreddit.top(time_filter="month", limit=limit)
    raise NotImplementedError


def main():
    # if not CLIENT_ID or not CLIENT_SECRET:
    #     print("Error: Reddit API credentials not configured in .env")
    #     return
    print("Reddit API credentials pending — registration in progress.")
    print(f"Subreddits configured: {len(SUBREDDITS)}")
    print(f"Output path: {OUTPUT_FILE}")
    print(f"Output columns: {COLUMNS}")
    return

    # reddit = get_reddit_client()
    # data = []
    #
    # for subreddit_name in SUBREDDITS:
    #     print(f"\nFetching r/{subreddit_name}...")
    #
    #     try:
    #         posts = fetch_posts(reddit, subreddit_name)
    #
    #         for post in posts:
    #             data.append({
    #                 "Post ID": post.id,
    #                 "Title": post.title,
    #                 "Post Text": getattr(post, "selftext", ""),
    #                 "Author": str(post.author) if post.author else "[deleted]",
    #                 "Created Date": time.strftime(
    #                     "%Y-%m-%dT%H:%M:%SZ", time.gmtime(post.created_utc)
    #                 ),
    #                 "Upvotes/Score": post.score,
    #                 "Comment Count": post.num_comments,
    #                 "Subreddit": str(post.subreddit),
    #             })
    #
    #         print(f"  Collected: {len(data)} total posts")
    #     except Exception as e:
    #         print(f"  Error r/{subreddit_name}: {e}")
    #
    #     time.sleep(1)
    #
    # df = pd.DataFrame(data, columns=COLUMNS)
    # OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    # df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    # print(f"\nDone! Total records: {len(df)}")


if __name__ == "__main__":
    main()
