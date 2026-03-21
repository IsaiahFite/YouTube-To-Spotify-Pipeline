from src.audio import download_audio
from unittest.mock import patch, MagicMock
from yt_dlp.utils import DownloadError
import pytest


@patch("src.audio.yt_dlp.YoutubeDL")
@patch("src.audio.Path.is_file")
def test_download_audio_success(mock_is_file, mock_ydl):
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
    with pytest.raises(RuntimeError, match="FFMPEG_LOCATION not set in environment variables"):
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
