from apify_client import ApifyClient
from dotenv import load_dotenv
import pandas as pd
import os

load_dotenv()

APIFY_API_KEY = os.getenv("APIFY_API_KEY")
ACTOR_ID = "apify/instagram-hashtag-scraper"

KEYWORDS = [
    "ChatGPT", "AI Agents", "Automation", "AWS",
    "Databricks", "Data Engineering", "Digital Marketing",
    "SEO", "Influencer Marketing", "Startup", "SaaS",
    "Digital Transformation",
]

POSTS_PER_KEYWORD = 100
OUTPUT_FILE = "data/raw/instagram_master_dataset.csv"


def get_client():
    return ApifyClient(APIFY_API_KEY)


def fetch_posts(client, keyword, limit=POSTS_PER_KEYWORD):
    hashtag = keyword.replace(" ", "")
    run_input = {"hashtags": [hashtag], "resultsLimit": limit}
    run = client.actor(ACTOR_ID).call(run_input=run_input)
    if run is None:
        return []
    return client.dataset(run.default_dataset_id).iterate_items()


def main():
    if not APIFY_API_KEY:
        print("Error: APIFY_API_KEY not set in .env file")
        return

    client = get_client()
    data = []

    for keyword in KEYWORDS:
        print(f"\nFetching: {keyword}")
        try:
            for post in fetch_posts(client, keyword):
                data.append({
                    "Keyword": keyword,
                    "Post ID": post.get("id"),
                    "Caption": post.get("caption"),
                    "Author": post.get("ownerUsername"),
                    "Published Date": post.get("timestamp"),
                    "Like Count": post.get("likesCount"),
                    "Comment Count": post.get("commentsCount"),
                    "Post URL": post.get("url"),
                })
            print(f"  Collected: {len(data)}")
        except Exception as e:
            print(f"  Error for {keyword}: {e}")

    df = pd.DataFrame(data)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\nDone! Total records: {len(df)}")


if __name__ == "__main__":
    main()
