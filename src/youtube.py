from dotenv import load_dotenv
from googleapiclient.discovery import build
import os
import html
from src.tracker import save_processed, get_most_recent_timestamp
load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
START_DATE = os.getenv("START_DATE")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def get_livestreams(channel_id):
    videos = []
    page_token = None
    timestamp = get_most_recent_timestamp()
    if timestamp and timestamp > START_DATE: # if we have a timestamp and it's after the start date, fetch first page of videos published after that timestamp
        published_after = timestamp
    else: # if no timestamp or it's before the start date, fetch all videos since the start date
        published_after = START_DATE
    while True:
        response = youtube.search().list(
            part="snippet", channelId=channel_id, 
            eventType="completed", 
            type="video",
            order="date",
            publishedAfter=published_after,
            pageToken=page_token).execute()
        videos.extend(response["items"])
        page_token = response.get("nextPageToken")
        if not page_token:
            break   
    unique_videos = deduplicate_videos(videos)
    video_details = get_video_details([video["id"]["videoId"] for video in unique_videos])
    return video_details

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

def get_video_details(video_ids):
    details = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        response = youtube.videos().list(part="snippet,contentDetails", id=",".join(chunk)).execute()
        details.extend(response["items"])
    return details

if __name__ == "__main__": #pragma: no cover
    livestreams = get_livestreams(YOUTUBE_CHANNEL_ID)
    print(livestreams[0])
    print(f"Number of livestreams: {len(livestreams)}")
    for item in livestreams:
        print(html.unescape(item["snippet"]["title"]))
        print(item["snippet"]["publishedAt"])
        print("---")