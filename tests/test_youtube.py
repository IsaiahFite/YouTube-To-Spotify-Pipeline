import pytest
from src.youtube import deduplicate_videos

def test_keeps_later_duplicate():
    # Arrange - create your fake data
    videos = [
        {"snippet": {"title": "Video A", "publishedAt": "2024-01-01T00:00:00Z"}},
        {"snippet": {"title": "Video A", "publishedAt": "2024-01-02T00:00:00Z"}},
        {"snippet": {"title": "Video B", "publishedAt": "2024-01-01T00:00:00Z"}},
        # your fake video objects go here
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