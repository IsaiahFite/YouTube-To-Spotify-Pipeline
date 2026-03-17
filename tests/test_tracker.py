import pytest
from src.tracker import save_processed, load_processed, get_most_recent_timestamp
from pathlib import Path
from tempfile import TemporaryDirectory
import os

@pytest.fixture(autouse=True)
def setup_and_teardown():
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

def test_save_and_load_processed_video():
    # Arrange
    timestamp = "2024-01-01T00:00:00Z"
    
    # Act
    save_processed(timestamp)
    processed_timestamps = load_processed()
    
    # Assert
    assert timestamp in processed_timestamps

def test_load_processed_no_file():
    # Arrange - ensure the file does not exist
    data_dir = Path("data")
    processed_file = data_dir / "processed.json"
    if processed_file.exists():
        processed_file.unlink()
    
    # Act
    processed_timestamps = load_processed()
    
    # Assert
    assert processed_timestamps == []

def test_save_multiple_videos():
    # Arrange
    timestamps = [
        "2024-01-01T00:00:00Z",
        "2024-01-02T00:00:00Z",
        "2024-01-03T00:00:00Z"
    ]
    
    # Act
    for ts in timestamps:
        save_processed(ts)
    processed_timestamps = load_processed()
    
    # Assert
    for ts in timestamps:
        assert ts in processed_timestamps

def test_get_most_recent_timestamp():
    # Arrange
    timestamps = [
        "2024-01-01T00:00:00Z",
        "2024-01-02T00:00:00Z",
        "2024-01-03T00:00:00Z"
    ]
    for ts in timestamps:
        save_processed(ts)
    
    # Act
    most_recent = get_most_recent_timestamp()
    
    # Assert
    assert most_recent == "2024-01-03T00:00:00Z"

def test_get_most_recent_timestamp_no_videos():
    # Arrange - no videos saved, so processed.json should be empty or not exist
    
    # Act
    most_recent = get_most_recent_timestamp()
    
    # Assert
    assert most_recent is None