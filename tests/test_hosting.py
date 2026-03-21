import pytest
from unittest.mock import patch, MagicMock
from github import GithubException
from src.hosting import upload_audio


@patch.dict("os.environ", {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "test/repo"})
@patch("src.hosting.Github")
def test_upload_audio_success(mock_github):
    """Test successful audio upload"""
    mock_asset = MagicMock()
    mock_asset.browser_download_url = "https://github.com/download/url"

    mock_release = MagicMock()
    mock_release.upload_asset.return_value = mock_asset

    mock_repo = MagicMock()
    mock_repo.get_release.return_value = mock_release

    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github.return_value = mock_github_instance

    result = upload_audio("audio.mp3")
    assert result == "https://github.com/download/url"


@patch.dict("os.environ", {"GITHUB_TOKEN": "", "GITHUB_REPO": ""})
def test_upload_audio_missing_env_vars():
    """Test missing environment variables"""
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN and GITHUB_REPO must be set"):
        upload_audio("audio.mp3")


@patch.dict("os.environ", {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "test/repo"})
@patch("src.hosting.Github")
def test_upload_audio_create_release(mock_github):
    """Test creating new release when it doesn't exist"""
    mock_asset = MagicMock()
    mock_asset.browser_download_url = "https://github.com/download/url"

    mock_release = MagicMock()
    mock_release.upload_asset.return_value = mock_asset

    mock_repo = MagicMock()
    mock_repo.get_release.side_effect = GithubException(404, {"message": "Not Found"})
    mock_repo.create_git_release.return_value = mock_release

    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github.return_value = mock_github_instance

    result = upload_audio("audio.mp3")
    assert result == "https://github.com/download/url"
    mock_repo.create_git_release.assert_called_once()


@patch.dict("os.environ", {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "test/repo"})
@patch("src.hosting.Github")
def test_upload_audio_file_not_found(mock_github):
    """Test file not found error"""
    mock_repo = MagicMock()
    mock_release = MagicMock()
    mock_release.upload_asset.side_effect = FileNotFoundError()
    mock_repo.get_release.return_value = mock_release

    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github.return_value = mock_github_instance

    with pytest.raises(RuntimeError, match="Audio file not found"):
        upload_audio("nonexistent.mp3")


@patch.dict("os.environ", {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "test/repo"})
@patch("src.hosting.Github")
def test_upload_audio_github_api_error(mock_github):
    """Test GitHub API error handling"""
    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.side_effect = GithubException(
        401, {"message": "Unauthorized"}
    )
    mock_github.return_value = mock_github_instance

    with pytest.raises(RuntimeError, match="GitHub API error: 401"):
        upload_audio("audio.mp3")
