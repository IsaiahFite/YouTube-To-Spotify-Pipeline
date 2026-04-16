from dotenv import load_dotenv
import os
from pathlib import Path
import re
import subprocess
from typing import Any, cast
import yt_dlp
from yt_dlp.utils import DownloadError

load_dotenv()


def trim_leading_silence(file_path: str) -> None:
    FFMPEG_LOCATION = os.getenv("FFMPEG_LOCATION")
    ffmpeg_bin = str(Path(FFMPEG_LOCATION) / "ffmpeg") if FFMPEG_LOCATION else "ffmpeg"

    detect = subprocess.run(  # noqa: S603
        [ffmpeg_bin, "-i", file_path, "-af", "silencedetect=noise=-50dB:d=0.5", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )

    starts = [float(m.group(1)) for m in re.finditer(r"silence_start:\s*([\d.]+)", detect.stderr)]
    ends = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(r"silence_end:\s*([\d.]+)\s*\|\s*silence_duration:\s*([\d.]+)", detect.stderr)]

    long_silences = [e for e in ends if e[1] >= 60 and e[0] <= 600]

    if long_silences:
        trim_silence(file_path, long_silences[-1][0])
        return

    if not starts or starts[0] > 0:
        return
    if not ends:
        return
    
    trim_silence(file_path, ends[0][0])

def trim_silence(file_path: str, trim_at: float) -> None:
    FFMPEG_LOCATION = os.getenv("FFMPEG_LOCATION")
    ffmpeg_bin = str(Path(FFMPEG_LOCATION) / "ffmpeg") if FFMPEG_LOCATION else "ffmpeg"

    tmp_path = file_path.removesuffix(".mp3") + ".tmp.mp3"
    subprocess.run(  # noqa: S603
        [ffmpeg_bin, "-y", "-ss", str(trim_at), "-i", file_path, "-acodec", "copy", tmp_path],
        capture_output=True,
        check=True,
    )
    os.replace(tmp_path, file_path)

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
        trim_leading_silence(output_path)
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
