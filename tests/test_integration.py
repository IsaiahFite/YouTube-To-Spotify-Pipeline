import os
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.audio import download_audio
from src.pipeline import run_pipeline
from src.youtube import get_livestreams

TEST_VIDEO_ID = os.getenv("TEST_VIDEO_ID")
FFMPEG_LOCATION = os.getenv("FFMPEG_LOCATION")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
START_DATE = os.getenv("START_DATE")


# ==============================================================================
# Audio download integration tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not TEST_VIDEO_ID or not FFMPEG_LOCATION,
    reason="TEST_VIDEO_ID and FFMPEG_LOCATION must be set",
)
def test_download_audio_real():
    assert TEST_VIDEO_ID  # already guaranteed by skipif, satisfies type checker
    with TemporaryDirectory() as temp_dir:
        result = download_audio(TEST_VIDEO_ID, temp_dir)

        output_file = Path(result)
        assert output_file.exists(), f"Expected audio file at {result}"
        assert output_file.stat().st_size > 0, "Audio file should not be empty"
        assert output_file.suffix == ".mp3", "Expected .mp3 output"
        assert output_file.name == f"{TEST_VIDEO_ID}.mp3"


# ==============================================================================
# YouTube API integration tests
# ==============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not all([YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, START_DATE]),
    reason="YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, and START_DATE must be set",
)
def test_get_livestreams_real():
    with TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        data_dir.mkdir()
        (data_dir / "processed.json").write_text("[]")

        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            results = get_livestreams(YOUTUBE_CHANNEL_ID)
        finally:
            os.chdir(original_cwd)

    assert isinstance(results, list)
    for video in results:
        assert "id" in video
        assert "snippet" in video
        assert "title" in video["snippet"]
        assert "publishedAt" in video["snippet"]
        assert "description" in video["snippet"]


# ==============================================================================
# Full pipeline integration tests (real download, mocked GitHub/YouTube API)
# ==============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not TEST_VIDEO_ID or not FFMPEG_LOCATION,
    reason="TEST_VIDEO_ID and FFMPEG_LOCATION must be set",
)
def test_pipeline_real_download():
    from unittest.mock import MagicMock
    from xml.etree.ElementTree import Element, SubElement

    assert TEST_VIDEO_ID  # already guaranteed by skipif, satisfies type checker
    fake_video = {
        "id": TEST_VIDEO_ID,
        "snippet": {
            "title": "Integration Test Video",
            "description": "Integration test description",
            "publishedAt": "2024-01-01T00:00:00Z",
        },
    }

    mock_rss = Element("rss")
    mock_channel = SubElement(mock_rss, "channel")
    mock_release = MagicMock()
    mock_assets = []

    with TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            with patch.dict("os.environ", {"YOUTUBE_CHANNEL_ID": "UCtest"}), \
                 patch("src.pipeline.get_livestreams", return_value=[fake_video]), \
                 patch("src.pipeline.fetch_feed", return_value=(mock_rss, mock_channel, mock_release, mock_assets)), \
                 patch("src.pipeline.upload_audio", return_value="https://example.com/audio.mp3") as mock_upload, \
                 patch("src.pipeline.update_feed") as mock_feed, \
                 patch("src.pipeline.save_processed") as mock_save:
                run_pipeline()
        finally:
            os.chdir(original_cwd)

    # The pipeline downloaded a real file, uploaded it, then cleaned up
    mock_upload.assert_called_once()
    upload_path = mock_upload.call_args[0][0]
    assert not Path(upload_path).exists(), "Pipeline should remove audio file after upload"

    mock_feed.assert_called_once()
    _, _, _, _, feed_title, feed_desc, feed_date, feed_audio_url, feed_guid = mock_feed.call_args[0]
    assert feed_title == "Integration Test Video"
    assert feed_desc == "Integration test description"
    assert feed_date == "2024-01-01T00:00:00Z"
    assert feed_audio_url == "https://example.com/audio.mp3"
    assert feed_guid == f"https://www.youtube.com/watch?v={TEST_VIDEO_ID}"
    mock_save.assert_called_once_with("2024-01-01T00:00:00Z")
