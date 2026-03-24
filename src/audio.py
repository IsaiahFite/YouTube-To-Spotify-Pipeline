from dotenv import load_dotenv
import os
from pathlib import Path
from typing import Any, cast
import yt_dlp
from yt_dlp.utils import DownloadError

load_dotenv()


def download_audio(video_id: str, save_path: str) -> str:
    FFMPEG_LOCATION = os.getenv("FFMPEG_LOCATION")
    if not FFMPEG_LOCATION:
        raise RuntimeError(
            "FFMPEG_LOCATION not set in environment variables. Please set FFMPEG_LOCATION to the path of your FFmpeg installation."
        )
    try:
        URL = f"https://www.youtube.com/watch?v={video_id}"
        yt_opts = cast(
            Any,
            {
                "format": "bestaudio/best",
                "outtmpl": f"{save_path}/%(id)s",
                "ffmpeg_location": FFMPEG_LOCATION,
                "remote_components": "ejs:github",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "0",  # Best quality (0 = highest, 5 = lowest)
                    }
                ],
            },
        )
        with yt_dlp.YoutubeDL(yt_opts) as ydl:
            ydl.download([URL])
        output_path = f"{save_path}/{video_id}.mp3"
        p = Path(output_path)
        if not p.is_file():
            raise RuntimeError(f"Failed to create audio file for video {video_id}")
        return output_path
    except DownloadError as e:
        raise RuntimeError(f"Failed to download video {video_id}: {e}")
    except FileNotFoundError as e:
        raise RuntimeError(
            f"Error: FFmpeg not found. Please ensure FFmpeg is correct in your environment variables. {e}"
        )
    # returns the file path on success
    # raises an exception on failure


if __name__ == "__main__":  # pragma: no cover
    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False
        )
        print(info.keys())
        result = download_audio("dQw4w9WgXcQ", "data/audio")
        print(result)
