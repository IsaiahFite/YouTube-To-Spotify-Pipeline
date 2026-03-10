from dotenv import load_dotenv
from googleapiclient.discovery import build
import os
import html
load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
START_DATE = os.getenv("START_DATE")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def get_livestreams(channel_id):
    response = youtube.search().list(
        part="snippet", channelId=channel_id, 
        eventType="completed", 
        type="video",
        order="date",
        publishedAfter=START_DATE).execute()
    unique_videos = deduplicate_videos(response["items"])
    return unique_videos

def deduplicate_videos(videos):
    videos_by_title = {}
    for item in videos:
        title = item["snippet"]["title"]
        if title not in videos_by_title:
            videos_by_title[title] = item
        else:
            existing_date = videos_by_title[title]["snippet"]["publishedAt"]
            new_date = item["snippet"]["publishedAt"]
            if new_date > existing_date:
                videos_by_title[title] = item
    return list(videos_by_title.values())

if __name__ == "__main__":
    livestreams = get_livestreams(YOUTUBE_CHANNEL_ID)
    print(f"Number of livestreams: {len(livestreams)}")
    for item in livestreams:
        print(html.unescape(item["snippet"]["title"]))
        print(item["snippet"]["publishedAt"])
        print("---")