from googleapiclient.discovery import build
from dotenv import load_dotenv
import time
import os

from collector_utils import save_incremental

load_dotenv()

API_KEY = os.getenv("API_KEY")
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

KEYWORDS = [
    "ChatGPT", "AI Agents", "Automation", "AWS",
    "Databricks", "Data Engineering", "Digital Marketing",
    "SEO", "Influencer Marketing", "Startup", "SaaS",
    "Digital Transformation",
]

OUTPUT_FILE = "data/raw/youtube_master_dataset.csv"


def get_youtube_client():
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)


def search_videos(youtube, keyword, max_results=10):
    response = youtube.search().list(
        q=keyword, part="snippet", type="video", maxResults=max_results
    ).execute()
    return response.get("items", [])


def get_comments(youtube, video_id, max_results=50):
    response = youtube.commentThreads().list(
        part="snippet", videoId=video_id, maxResults=max_results
    ).execute()
    return response.get("items", [])


def main():
    if not API_KEY:
        print("Error: API_KEY not set in .env file")
        return

    youtube = get_youtube_client()
    data = []

    for keyword in KEYWORDS:
        print(f"\nSearching: {keyword}")

        videos = search_videos(youtube, keyword)
        for video in videos:
            if "videoId" not in video.get("id", {}):
                continue

            video_id = video["id"]["videoId"]
            video_title = video["snippet"]["title"]

            try:
                comments = get_comments(youtube, video_id)
                for comment in comments:
                    snippet = comment["snippet"]["topLevelComment"]["snippet"]
                    data.append({
                        "Keyword": keyword,
                        "Video ID": video_id,
                        "Video Title": video_title,
                        "Comment Text": snippet["textDisplay"],
                        "Author": snippet["authorDisplayName"],
                        "Published Date": snippet["publishedAt"],
                        "Like Count": snippet["likeCount"],
                    })

                print(f"  Collected: {len(data)}")
            except Exception as e:
                print(f"  Comment Error for {video_id}: {e}")

            time.sleep(1)

    save_incremental(data, OUTPUT_FILE, key_cols=["Video ID", "Author", "Comment Text"])


if __name__ == "__main__":
    main()
