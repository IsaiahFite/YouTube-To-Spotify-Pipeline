import pytest
from unittest.mock import patch, call, MagicMock
from xml.etree.ElementTree import Element, SubElement
from src.pipeline import run_pipeline


def make_video(video_id, title="Test Title", description="Test Description", pub_date="2024-01-01T00:00:00Z"):
    return {
        "id": video_id,
        "snippet": {
            "title": title,
            "description": description,
            "publishedAt": pub_date,
        }
    }


def _make_fetch_feed_return():
    """Return a realistic fetch_feed() tuple with an empty channel."""
    rss = Element("rss")
    channel = SubElement(rss, "channel")
    release = MagicMock()
    assets = []
    return rss, channel, release, assets


@patch.dict("os.environ", {"YOUTUBE_CHANNEL_ID": ""})
def test_run_pipeline_missing_channel_id():
    # Arrange / Act / Assert
    with pytest.raises(RuntimeError, match="YOUTUBE_CHANNEL_ID must be set"):
        run_pipeline()


@patch.dict("os.environ", {"YOUTUBE_CHANNEL_ID": "UCtest"})
def test_run_pipeline_no_videos(capsys):
    # Act
    with patch("src.pipeline.get_livestreams", return_value=[]), \
         patch("src.pipeline.os.makedirs"):
        run_pipeline()

    # Assert
    captured = capsys.readouterr()
    assert "No new videos found." in captured.out


@patch.dict("os.environ", {"YOUTUBE_CHANNEL_ID": "UCtest"})
@patch("src.pipeline.os.remove")
@patch("src.pipeline.save_processed")
@patch("src.pipeline.update_feed")
@patch("src.pipeline.upload_audio", return_value="https://example.com/audio.mp3")
@patch("src.pipeline.download_audio", return_value="data/audio/vid1.mp3")
@patch("src.pipeline.fetch_feed")
@patch("src.pipeline.get_livestreams")
def test_run_pipeline_success(
    mock_get_livestreams, mock_fetch_feed, mock_download, mock_upload,
    mock_update_feed, mock_save, mock_remove
):
    # Arrange — title contains an HTML entity to confirm unescaping
    video = make_video("vid1", title="My &amp; Title", description="My desc", pub_date="2024-01-01T00:00:00Z")
    mock_get_livestreams.return_value = [video]
    rss, channel, release, assets = _make_fetch_feed_return()
    mock_fetch_feed.return_value = (rss, channel, release, assets)

    # Act
    with patch("src.pipeline.os.makedirs"):
        run_pipeline()

    # Assert — each step called with the correct arguments
    mock_download.assert_called_once_with("vid1", "data/audio")
    mock_upload.assert_called_once_with("data/audio/vid1.mp3")
    mock_update_feed.assert_called_once_with(
        rss, channel, release, assets,
        "My & Title",
        "My desc",
        "2024-01-01T00:00:00Z",
        "https://example.com/audio.mp3",
        "https://www.youtube.com/watch?v=vid1",
    )
    mock_save.assert_called_once_with("2024-01-01T00:00:00Z")
    mock_remove.assert_called_once_with("data/audio/vid1.mp3")


@patch.dict("os.environ", {"YOUTUBE_CHANNEL_ID": "UCtest"})
@patch("src.pipeline.fetch_feed")
@patch("src.pipeline.download_audio", return_value="data/audio/vid1.mp3")
@patch("src.pipeline.get_livestreams")
def test_run_pipeline_processes_videos_oldest_first(mock_get_livestreams, mock_download, mock_fetch_feed):
    # Arrange — get_livestreams returns newest-first as the YouTube API does
    videos = [
        make_video("vid_new", pub_date="2024-01-03T00:00:00Z"),
        make_video("vid_mid", pub_date="2024-01-02T00:00:00Z"),
        make_video("vid_old", pub_date="2024-01-01T00:00:00Z"),
    ]
    mock_get_livestreams.return_value = videos
    mock_fetch_feed.return_value = _make_fetch_feed_return()

    # Act
    with patch("src.pipeline.os.makedirs"), \
         patch("src.pipeline.upload_audio", return_value="https://example.com/audio.mp3"), \
         patch("src.pipeline.update_feed"), \
         patch("src.pipeline.save_processed"), \
         patch("src.pipeline.os.remove"):
        run_pipeline()

    # Assert — processed oldest-first so the RSS feed builds in chronological order
    assert mock_download.call_args_list == [
        call("vid_old", "data/audio"),
        call("vid_mid", "data/audio"),
        call("vid_new", "data/audio"),
    ]


@patch.dict("os.environ", {"YOUTUBE_CHANNEL_ID": "UCtest"})
@patch("src.pipeline.fetch_feed")
@patch("src.pipeline.get_livestreams")
def test_run_pipeline_get_livestreams_retry_succeeds(mock_get_livestreams, mock_fetch_feed, capsys):
    # Arrange — first call fails, second succeeds
    video = make_video("vid1")
    mock_get_livestreams.side_effect = [Exception("API error"), [video]]
    mock_fetch_feed.return_value = _make_fetch_feed_return()

    # Act
    with patch("src.pipeline.os.makedirs"), \
         patch("src.pipeline.download_audio", return_value="data/audio/vid1.mp3"), \
         patch("src.pipeline.upload_audio", return_value="https://example.com/audio.mp3"), \
         patch("src.pipeline.update_feed"), \
         patch("src.pipeline.save_processed"), \
         patch("src.pipeline.os.remove"):
        run_pipeline()

    # Assert
    assert mock_get_livestreams.call_count == 2
    captured = capsys.readouterr()
    assert "Retrying" in captured.out


@patch.dict("os.environ", {"YOUTUBE_CHANNEL_ID": "UCtest"})
@patch("src.pipeline.get_livestreams", side_effect=Exception("API error"))
def test_run_pipeline_get_livestreams_fails_both_attempts(mock_get_livestreams):
    # Act / Assert
    with patch("src.pipeline.os.makedirs"):
        with pytest.raises(RuntimeError, match="Pipeline requires maintenance"):
            run_pipeline()
    assert mock_get_livestreams.call_count == 2


@patch.dict("os.environ", {"YOUTUBE_CHANNEL_ID": "UCtest"})
@patch("src.pipeline.fetch_feed")
@patch("src.pipeline.get_livestreams")
def test_run_pipeline_video_processing_retry_succeeds(mock_get_livestreams, mock_fetch_feed, capsys):
    # Arrange — first download fails, second succeeds
    video = make_video("vid1")
    mock_get_livestreams.return_value = [video]
    mock_fetch_feed.return_value = _make_fetch_feed_return()

    # Act
    with patch("src.pipeline.os.makedirs"), \
         patch("src.pipeline.download_audio", side_effect=[RuntimeError("Download failed"), "data/audio/vid1.mp3"]) as mock_download, \
         patch("src.pipeline.upload_audio", return_value="https://example.com/audio.mp3"), \
         patch("src.pipeline.update_feed"), \
         patch("src.pipeline.save_processed"), \
         patch("src.pipeline.os.remove"):
        run_pipeline()

    # Assert
    assert mock_download.call_count == 2
    captured = capsys.readouterr()
    assert "Retrying" in captured.out


@patch.dict("os.environ", {"YOUTUBE_CHANNEL_ID": "UCtest"})
@patch("src.pipeline.fetch_feed")
@patch("src.pipeline.get_livestreams")
def test_run_pipeline_video_processing_fails_both_attempts(mock_get_livestreams, mock_fetch_feed):
    # Arrange
    video = make_video("vid1")
    mock_get_livestreams.return_value = [video]
    mock_fetch_feed.return_value = _make_fetch_feed_return()

    # Act / Assert
    with patch("src.pipeline.os.makedirs"), \
         patch("src.pipeline.download_audio", side_effect=RuntimeError("Download failed")):
        with pytest.raises(RuntimeError, match="Pipeline requires maintenance"):
            run_pipeline()


@patch.dict("os.environ", {"YOUTUBE_CHANNEL_ID": "UCtest"})
@patch("src.pipeline.os.remove")
@patch("src.pipeline.fetch_feed")
@patch("src.pipeline.get_livestreams")
def test_run_pipeline_cleans_up_file_on_error(mock_get_livestreams, mock_fetch_feed, mock_remove):
    # Arrange — download succeeds but upload always fails
    video = make_video("vid1")
    mock_get_livestreams.return_value = [video]
    mock_fetch_feed.return_value = _make_fetch_feed_return()

    # Act / Assert
    with patch("src.pipeline.os.makedirs"), \
         patch("src.pipeline.os.path.exists", return_value=True), \
         patch("src.pipeline.download_audio", return_value="data/audio/vid1.mp3"), \
         patch("src.pipeline.upload_audio", side_effect=RuntimeError("Upload failed")):
        with pytest.raises(RuntimeError, match="Pipeline requires maintenance"):
            run_pipeline()

    # Cleanup should fire once per failed attempt (2 total)
    assert mock_remove.call_count == 2
    mock_remove.assert_called_with("data/audio/vid1.mp3")


@patch.dict("os.environ", {"YOUTUBE_CHANNEL_ID": "UCtest"})
@patch("src.pipeline.os.makedirs")
def test_run_pipeline_creates_audio_directory(mock_makedirs):
    # Act
    with patch("src.pipeline.get_livestreams", return_value=[]):
        run_pipeline()

    # Assert
    mock_makedirs.assert_called_once_with("data/audio", exist_ok=True)
