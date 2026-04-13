from src.audio import download_audio, trim_leading_silence
from unittest.mock import patch, MagicMock, call
from yt_dlp.utils import DownloadError
import pytest


# ---------------------------------------------------------------------------
# download_audio
# ---------------------------------------------------------------------------

@patch("src.audio.trim_leading_silence")
@patch("src.audio.yt_dlp.YoutubeDL")
@patch("src.audio.Path.is_file")
def test_download_audio_success(mock_is_file, mock_ydl, mock_trim):
    mock_instance = MagicMock()
    mock_ydl.return_value.__enter__.return_value = mock_instance
    mock_is_file.return_value = True

    video_id = "test_video_id"
    save_path = "test_save_path"
    expected_path = f"{save_path}/{video_id}.mp3"
    result = download_audio(video_id, save_path)
    mock_instance.download.assert_called_once_with(
        [f"https://www.youtube.com/watch?v={video_id}"]
    )
    assert result == expected_path


@patch("src.audio.os.getenv", return_value=None)
def test_download_audio_ffmpeg_location_not_set(mock_getenv):
    video_id = "test_video_id"
    save_path = "test_save_path"
    with pytest.raises(
        RuntimeError, match="FFMPEG_LOCATION not set in environment variables"
    ):
        download_audio(video_id, save_path)


@patch("src.audio.yt_dlp.YoutubeDL")
@patch("src.audio.Path.is_file")
def test_download_audio_file_not_created(mock_is_file, mock_ydl):
    mock_instance = MagicMock()
    mock_ydl.return_value.__enter__.return_value = mock_instance
    mock_is_file.return_value = False
    video_id = "test_video_id"
    save_path = "test_save_path"
    with pytest.raises(RuntimeError, match="Failed to create audio file"):
        download_audio(video_id, save_path)


@patch("src.audio.yt_dlp.YoutubeDL")
def test_download_audio_download_error(mock_ydl):
    mock_instance = MagicMock()
    mock_instance.download.side_effect = DownloadError("Download failed")
    mock_ydl.return_value.__enter__.return_value = mock_instance
    video_id = "test_video_id"
    save_path = "test_save_path"
    with pytest.raises(RuntimeError, match="Failed to download video"):
        download_audio(video_id, save_path)


@patch("src.audio.yt_dlp.YoutubeDL")
def test_download_audio_ffmpeg_not_found(mock_ydl):
    mock_instance = MagicMock()
    mock_instance.download.side_effect = FileNotFoundError("FFmpeg not found")
    mock_ydl.return_value.__enter__.return_value = mock_instance
    video_id = "test_video_id"
    save_path = "test_save_path"
    with pytest.raises(RuntimeError, match="FFmpeg not found"):
        download_audio(video_id, save_path)


@patch("src.audio.trim_leading_silence")
@patch("src.audio.yt_dlp.YoutubeDL")
@patch("src.audio.Path.is_file")
def test_download_audio_calls_trim(mock_is_file, mock_ydl, mock_trim):
    """download_audio calls trim_leading_silence with the output path."""
    mock_ydl.return_value.__enter__.return_value = MagicMock()
    mock_is_file.return_value = True

    download_audio("vid1", "data/audio")

    mock_trim.assert_called_once_with("data/audio/vid1.mp3")


# ---------------------------------------------------------------------------
# trim_leading_silence
# ---------------------------------------------------------------------------

@patch("src.audio.subprocess.run")
def test_trim_leading_silence_no_silence(mock_run):
    """No silence in stderr — function returns without trimming."""
    mock_run.return_value = MagicMock(stderr="")

    trim_leading_silence("test.mp3")

    mock_run.assert_called_once()


@patch("src.audio.subprocess.run")
def test_trim_leading_silence_non_leading(mock_run):
    """Silence starts mid-file — function returns without trimming."""
    mock_run.return_value = MagicMock(
        stderr="[silencedetect] silence_start: 5.0\n[silencedetect] silence_end: 6.0 | silence_duration: 1.0\n"
    )

    trim_leading_silence("test.mp3")

    mock_run.assert_called_once()


@patch("src.audio.os.replace")
@patch("src.audio.subprocess.run")
def test_trim_leading_silence_trims(mock_run, mock_replace):
    """Leading silence detected — ffmpeg trim is called and file is replaced."""
    mock_run.return_value = MagicMock(
        stderr="[silencedetect] silence_start: 0\n[silencedetect] silence_end: 2.5 | silence_duration: 2.5\n"
    )

    trim_leading_silence("test.mp3")

    assert mock_run.call_count == 2
    mock_replace.assert_called_once_with("test.mp3.tmp", "test.mp3")


@patch("src.audio.subprocess.run")
def test_trim_leading_silence_silence_fills_file(mock_run):
    """silence_start is 0 but no silence_end — entire file is silent, skip trim."""
    mock_run.return_value = MagicMock(
        stderr="[silencedetect] silence_start: 0\n"
    )

    trim_leading_silence("test.mp3")

    mock_run.assert_called_once()
