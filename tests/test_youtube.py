import pytest
from src.youtube import deduplicate_videos, get_livestreams
from src.tracker import save_processed, load_processed, get_most_recent_timestamp
from unittest.mock import patch, MagicMock
from pathlib import Path
from tempfile import TemporaryDirectory
import os

@pytest.fixture(autouse=False)
def setup_and_teardown_empty():
    with TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        processed_file = data_dir / "processed.json"
        processed_file.write_text("[]")
        
        # Change the working directory to the temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        yield  # Run the tests
        
        # Change back to the original working directory
        os.chdir(original_cwd)

@pytest.fixture(autouse=False)
def setup_and_teardown():
    with TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        processed_file = data_dir / "processed.json"
        processed_file.write_text(
            "[\"2024-01-01T00:00:00Z\", \"2024-01-02T00:00:00Z\"]"
        )
        
        # Change the working directory to the temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        yield  # Run the tests
        
        # Change back to the original working directory
        os.chdir(original_cwd)

# ==============================================================================
# YouTube Search tests
# ==============================================================================
@patch("src.youtube.youtube")
def test_get_livestreams(mock_youtube, setup_and_teardown_empty):
    # Arrange - set up the mock response
    mock_youtube.search().list().execute.return_value = {
        "items": [
            {"id": {"videoId": "video1"}, "snippet": {"title": "Video A", "publishedAt": "2024-01-01T00:00:00Z"}},
            {"id": {"videoId": "video2"}, "snippet": {"title": "Video B", "publishedAt": "2024-01-02T00:00:00Z"}},
        ]
    }
    mock_youtube.videos().list().execute.return_value = {
        "items": [
            {"id": {"videoId": "video1"}, "snippet": {"title": "Video A", "publishedAt": "2024-01-01T00:00:00Z"}, "contentDetails": {"duration": "PT10M"}},
            {"id": {"videoId": "video2"}, "snippet": {"title": "Video B", "publishedAt": "2024-01-02T00:00:00Z"}, "contentDetails": {"duration": "PT20M"}},
        ]
    }
    # Act - call the function
    livestreams = get_livestreams("fake_channel_id")
    # Assert - check the output
    assert len(livestreams) == 2
    assert livestreams[0]["snippet"]["title"] == "Video A"
    assert livestreams[1]["snippet"]["title"] == "Video B"
    assert livestreams[0]["snippet"]["publishedAt"] == "2024-01-01T00:00:00Z"
    assert livestreams[1]["snippet"]["publishedAt"] == "2024-01-02T00:00:00Z"

@patch("src.youtube.youtube")
def test_get_livestreams_no_videos(mock_youtube, setup_and_teardown_empty):
    # Arrange - set up the mock response with no items
    mock_youtube.search().list().execute.return_value = {"items": []}
    # Act - call the function
    livestreams = get_livestreams("fake_channel_id")
    # Assert - check the output is an empty list
    assert livestreams == []

# ==============================================================================
# Deduplication tests
# ==============================================================================
@patch("src.youtube.youtube")
def test_get_livestreams_with_duplicates(mock_youtube, setup_and_teardown_empty):
    # Arrange - set up the mock response with duplicate titles
    mock_youtube.search().list().execute.return_value = {
        "items": [
            {"id": {"videoId": "video1"}, "snippet": {"title": "Video A", "publishedAt": "2024-01-01T00:00:00Z"}},
            {"id": {"videoId": "video2"}, "snippet": {"title": "Video A", "publishedAt": "2024-01-02T00:00:00Z"}},
            {"id": {"videoId": "video3"}, "snippet": {"title": "Video B", "publishedAt": "2024-01-01T00:00:00Z"}},
        ]
    }
    mock_youtube.videos().list().execute.return_value = {
        "items": [
            {"id": {"videoId": "video1"}, "snippet": {"title": "Video A", "publishedAt": "2024-01-02T00:00:00Z"}, "contentDetails": {"duration": "PT10M"}},
            {"id": {"videoId": "video2"}, "snippet": {"title": "Video B", "publishedAt": "2024-01-01T00:00:00Z"}, "contentDetails": {"duration": "PT20M"}},
        ]
    }
    # Act - call the function
    livestreams = get_livestreams("fake_channel_id")
    # Assert - check that duplicates are removed and the later one is kept
    assert len(livestreams) == 2
    assert livestreams[0]["snippet"]["title"] == "Video A"
    assert livestreams[0]["snippet"]["publishedAt"] == "2024-01-02T00:00:00Z"
    assert livestreams[1]["snippet"]["title"] == "Video B"
    assert livestreams[1]["snippet"]["publishedAt"] == "2024-01-01T00:00:00Z"


def test_keeps_later_duplicate():
    # Arrange
    videos = [
        {"snippet": {"title": "Video A", "publishedAt": "2024-01-01T00:00:00Z"}},
        {"snippet": {"title": "Video A", "publishedAt": "2024-01-02T00:00:00Z"}},
        {"snippet": {"title": "Video B", "publishedAt": "2024-01-01T00:00:00Z"}},
    ]
    
    # Act - call the function
    result = deduplicate_videos(videos)
    
    # Assert - check the output
    assert len(result) == 2
    assert result[0]["snippet"]["publishedAt"] == "2024-01-02T00:00:00Z"
    assert result[1]["snippet"]["publishedAt"] == "2024-01-01T00:00:00Z"

def test_returns_empty_list_for_no_videos():
    # Arrange
    videos = []
    
    # Act
    result = deduplicate_videos(videos)
    
    # Assert
    assert result == []

def test_no_duplicates():
    # Arrange
    videos = [
        {"snippet": {"title": "Video A", "publishedAt": "2024-01-01T00:00:00Z"}},
        {"snippet": {"title": "Video B", "publishedAt": "2024-01-02T00:00:00Z"}},
    ]
    
    # Act
    result = deduplicate_videos(videos)
    
    # Assert
    assert len(result) == 2
    assert result[0]["snippet"]["publishedAt"] == "2024-01-01T00:00:00Z"
    assert result[1]["snippet"]["publishedAt"] == "2024-01-02T00:00:00Z"

def test_all_duplicates():
    # Arrange
    videos = [
        {"snippet": {"title": "Video A", "publishedAt": "2024-01-01T00:00:00Z"}},
        {"snippet": {"title": "Video A", "publishedAt": "2024-01-02T00:00:00Z"}},
        {"snippet": {"title": "Video A", "publishedAt": "2024-01-03T00:00:00Z"}},
    ]
    
    # Act
    result = deduplicate_videos(videos)
    
    # Assert
    assert len(result) == 1
    assert result[0]["snippet"]["publishedAt"] == "2024-01-03T00:00:00Z"

# ==============================================================================
# Pagination and timestamp filtering tests
# ==============================================================================
@patch("src.youtube.youtube")
def test_pagination(mock_youtube, setup_and_teardown_empty):
    # Arrange - set up the mock response with pagination
    mock_youtube.search().list().execute.side_effect = [
        {"items": [{"id": {"videoId": "video1"}, "snippet": {"title": "Video A", "publishedAt": "2024-01-01T00:00:00Z"}}], "nextPageToken": "token1"},
        {"items": [{"id": {"videoId": "video2"}, "snippet": {"title": "Video B", "publishedAt": "2024-01-02T00:00:00Z"}}]},
    ]
    mock_youtube.videos().list().execute.return_value = {
        "items": [
            {"id": {"videoId": "video1"}, "snippet": {"title": "Video A"}, "contentDetails": {"duration": "PT10M"}},
            {"id": {"videoId": "video2"}, "snippet": {"title": "Video B"}, "contentDetails": {"duration": "PT20M"}},
        ]
    }
    # Act - call the function
    livestreams = get_livestreams("fake_channel_id")
    
    # Assert - check that both pages of results are combined
    assert len(livestreams) == 2
    assert livestreams[0]["snippet"]["title"] == "Video A"
    assert livestreams[1]["snippet"]["title"] == "Video B"

@patch("src.youtube.youtube")
@patch("src.youtube.START_DATE", "2024-01-01T00:00:00Z")
def test_fetches_videos_after_timestamp(mock_youtube, setup_and_teardown):
    # Arrange - set up the mock response
    mock_youtube.search().list().execute.return_value = {
        "items": []
    }
    # Act - call the function with a timestamp that should filter out the first video
    livestreams = get_livestreams("fake_channel_id")
    
    # Assert - check that only the second video is returned
    mock_youtube.search().list.assert_called_with(
        part="snippet", 
        channelId="fake_channel_id",
        eventType="completed",
        type="video",
        order="date",
        publishedAfter="2024-01-02T00:00:00Z",
        pageToken=None
    )

# ==============================================================================
# Youtube Video Details tests
# ==============================================================================
@patch("src.youtube.youtube")
def test_get_video_details(mock_youtube, setup_and_teardown_empty):
    # Arrange - set up the mock response
    with patch("src.youtube.youtube") as mock_youtube:
        mock_youtube.videos().list().execute.return_value = {
            "items": [
                {"id": {"videoId": "video1"}, "snippet": {"title": "Video 1"}, "contentDetails": {"duration": "PT10M"}},
                {"id": {"videoId": "video2"}, "snippet": {"title": "Video 2"}, "contentDetails": {"duration": "PT20M"}},
            ]
        }
        # Act - call the function
        from src.youtube import get_video_details
        details = get_video_details(["video1", "video2"])
        # Assert - check the output
        assert len(details) == 2
        assert details[0]["id"]["videoId"] == "video1"
        assert details[0]["snippet"]["title"] == "Video 1"
        assert details[0]["contentDetails"]["duration"] == "PT10M"
        assert details[1]["id"]["videoId"] == "video2"
        assert details[1]["snippet"]["title"] == "Video 2"
        assert details[1]["contentDetails"]["duration"] == "PT20M"

@patch("src.youtube.youtube")
def test_get_video_details_empty(mock_youtube, setup_and_teardown_empty):
    # Arrange - set up the mock response for empty video IDs
    with patch("src.youtube.youtube") as mock_youtube:
        mock_youtube.videos().list().execute.return_value = {"items": []}
        # Act - call the function with an empty list
        from src.youtube import get_video_details
        details = get_video_details([])
        # Assert - check that the output is an empty list
        assert details == []

# ==============================================================================
# Youtube Video Details pagination tests
# ==============================================================================
@patch("src.youtube.youtube")
def test_get_video_details_pagination(mock_youtube, setup_and_teardown_empty):
    # Arrange - set up the mock response for more than 50 video IDs
    video_ids = [f"video{i}" for i in range(1, 101)]
    with patch("src.youtube.youtube") as mock_youtube:
        mock_youtube.videos().list().execute.side_effect = [
            {"items": [{"id": {"videoId": f"video{i}"}, "snippet": {"title": f"Video {i}"}, "contentDetails": {"duration": f"PT{i}M"}} for i in range(1, 51)]},
            {"items": [{"id": {"videoId": f"video{i}"}, "snippet": {"title": f"Video {i}"}, "contentDetails": {"duration": f"PT{i}M"}} for i in range(51, 101)]},
        ]
        # Act - call the function
        from src.youtube import get_video_details
        details = get_video_details(video_ids)
        # Assert - check that all video details are returned correctly
        assert len(details) == 100
        for i in range(1, 101):
            assert details[i-1]["id"]["videoId"] == f"video{i}"
            assert details[i-1]["snippet"]["title"] == f"Video {i}"
            assert details[i-1]["contentDetails"]["duration"] == f"PT{i}M"