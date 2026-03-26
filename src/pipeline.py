from src.youtube import get_livestreams
from src.audio import download_audio
from src.hosting import upload_audio
from src.rss import update_feed
from src.tracker import save_processed
from dotenv import load_dotenv
import html
import os

load_dotenv()

def run_pipeline() -> None:
    # Ensure required environment variable is present before doing any work
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
    if not YOUTUBE_CHANNEL_ID:
        raise RuntimeError(
            "YOUTUBE_CHANNEL_ID must be set in environment variables"
        )

    # Ensure the local audio staging directory exists before any downloads
    os.makedirs("data/audio", exist_ok=True)

    # Fetch new videos from YouTube, with one retry in case of transient API errors
    videos = []
    for attempt in range(2):
        try:
            videos = get_livestreams(YOUTUBE_CHANNEL_ID)
            break
        except Exception as e:
            if attempt == 0:
                print(f"Error fetching livestreams: {e}. Retrying...")
            else:
                raise RuntimeError(
                    f"Failed to fetch livestreams on retry. Pipeline requires maintenance: {e}"
                ) from e

    # Nothing new to process since the last run
    if not videos:
        print("No new videos found.")
        return

    for video in reversed(videos):
        # Extract and decode episode metadata from the YouTube API response
        video_id = video["id"]
        title = html.unescape(video["snippet"]["title"])
        description = html.unescape(video["snippet"]["description"])
        pub_date = video["snippet"]["publishedAt"]
        # Use the full YouTube URL as the globally unique episode identifier in the RSS feed
        guid = f"https://www.youtube.com/watch?v={video_id}"
        local_path = None

        # Process each video with one retry; stop the pipeline if the retry also fails
        for attempt in range(2):
            try:
                # Download audio locally, upload to hosting, update the RSS feed, then record and clean up
                local_path = download_audio(video_id, "data/audio")
                audio_url = upload_audio(local_path)
                update_feed(title, description, pub_date, audio_url, guid)
                save_processed(pub_date)
                os.remove(local_path)
                break
            except RuntimeError as e:
                if "already exists in feed" in str(e):
                    # Already processed, just mark it done and move on
                    save_processed(pub_date)
                    if local_path and os.path.exists(local_path):
                        os.remove(local_path)
                    break
                # Clean up any partially downloaded file before retrying or raising
                if local_path and os.path.exists(local_path):
                    os.remove(local_path)
                if attempt == 0:
                    print(f"Error processing video {video_id}: {e}. Retrying...")
                else:
                    raise RuntimeError(
                        f"Video {video_id} failed on retry. Pipeline requires maintenance: {e}"
                    ) from e

if __name__ == "__main__":  # pragma: no cover
    run_pipeline()