import pytest
import os
from unittest.mock import patch, MagicMock
from github import GithubException
from xml.etree.ElementTree import tostring, Element, SubElement
from src.rss import update_feed

FULL_ENV = {
    "GITHUB_TOKEN": "test_token",
    "GITHUB_REPO": "test/repo",
    "PODCAST_TITLE": "Test Podcast",
    "PODCAST_DESCRIPTION": "Test Description",
    "PODCAST_LINK": "http://test.com",
    "PODCAST_LANGUAGE": "en",
    "PODCAST_IMAGE": "http://test.com/image.jpg",
    "PODCAST_AUTHOR": "Test Author",
    "PODCAST_EMAIL": "test@example.com",
}


def _make_feed_xml(guids=None):
    """Build a minimal RSS feed XML as bytes."""
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "Test Podcast"
    if guids:
        for guid in guids:
            item = SubElement(channel, "item")
            SubElement(item, "guid").text = guid
    return tostring(rss, encoding="utf-8", method="xml")


@patch.dict("os.environ", {"GITHUB_TOKEN": "", "GITHUB_REPO": ""})
def test_missing_github_env_vars():
    """Test that missing GitHub env vars raise RuntimeError."""
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN and GITHUB_REPO must be set"):
        update_feed("title", "desc", "2024-01-01", "http://audio.mp3", "guid-1")


@patch.dict(
    "os.environ",
    {
        "GITHUB_TOKEN": "test_token",
        "GITHUB_REPO": "test/repo",
        "PODCAST_TITLE": "",
        "PODCAST_DESCRIPTION": "",
        "PODCAST_LINK": "",
        "PODCAST_LANGUAGE": "",
        "PODCAST_IMAGE": "",
    },
)
def test_missing_podcast_env_vars():
    """Test that missing podcast env vars raise RuntimeError."""
    with pytest.raises(RuntimeError, match="PODCAST_TITLE"):
        update_feed("title", "desc", "2024-01-01", "http://audio.mp3", "guid-1")


@patch.dict(
    "os.environ",
    {
        "GITHUB_TOKEN": "test_token",
        "GITHUB_REPO": "test/repo",
        "PODCAST_TITLE": "Test Podcast",
        "PODCAST_DESCRIPTION": "Test Description",
        "PODCAST_LINK": "http://test.com",
        "PODCAST_LANGUAGE": "en",
        "PODCAST_IMAGE": "http://test.com/image.jpg",
        "PODCAST_AUTHOR": "",
        "PODCAST_EMAIL": "",
    },
)
def test_missing_author_email_env_vars():
    """Test that missing PODCAST_AUTHOR or PODCAST_EMAIL raises RuntimeError."""
    with pytest.raises(RuntimeError, match="PODCAST_AUTHOR and PODCAST_EMAIL must be set"):
        update_feed("title", "desc", "2024-01-01", "http://audio.mp3", "guid-1")


@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
@patch("src.rss.requests")
@patch("src.rss.os.remove")
def test_new_feed_contains_author_and_email(_mock_remove, mock_requests, mock_github):
    """Test that a newly created feed includes itunes:author and itunes:email."""
    mock_release = MagicMock()
    mock_release.get_assets.return_value = []

    mock_repo = MagicMock()
    mock_repo.get_release.return_value = mock_release

    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github.return_value = mock_github_instance

    mock_requests.head.return_value.headers = {"Content-Length": "1000"}

    update_feed(
        "Episode 1",
        "Desc",
        "Mon, 01 Jan 2024 00:00:00 +0000",
        "http://audio.mp3",
        "guid-1",
    )

    temp_path = mock_release.upload_asset.call_args[1]["path"]
    with open(temp_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    assert "Test Author" in xml_content
    assert "test@example.com" in xml_content

    os.remove(temp_path)


@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
@patch("src.rss.requests")
def test_create_new_rss_feed(mock_requests, mock_github):
    """Test creating a new RSS feed when no feed.xml asset exists."""
    mock_release = MagicMock()
    mock_release.get_assets.return_value = []

    mock_repo = MagicMock()
    mock_repo.get_release.return_value = mock_release

    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github.return_value = mock_github_instance

    mock_requests.head.return_value.headers = {"Content-Length": "1000"}

    update_feed(
        "Episode 1",
        "Desc",
        "Mon, 01 Jan 2024 00:00:00 +0000",
        "http://audio.mp3",
        "guid-1",
    )

    mock_release.upload_asset.assert_called_once()
    call_kwargs = mock_release.upload_asset.call_args[1]
    assert call_kwargs["name"] == "feed.xml"
    assert call_kwargs["label"] == "Podcast RSS Feed"


@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
@patch("src.rss.requests")
def test_update_existing_rss_feed(mock_requests, mock_github):
    """Test updating an existing RSS feed by downloading, appending, and re-uploading."""
    existing_xml = _make_feed_xml()

    mock_asset = MagicMock()
    mock_asset.name = "feed.xml"
    mock_asset.browser_download_url = "http://example.com/feed.xml"

    mock_release = MagicMock()
    mock_release.get_assets.return_value = [mock_asset]

    mock_repo = MagicMock()
    mock_repo.get_release.return_value = mock_release

    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github.return_value = mock_github_instance

    mock_requests.get.return_value.content = existing_xml
    mock_requests.head.return_value.headers = {"Content-Length": "1000"}

    update_feed(
        "Episode 1",
        "Desc",
        "Mon, 01 Jan 2024 00:00:00 +0000",
        "http://audio.mp3",
        "guid-1",
    )

    mock_requests.get.assert_called_once_with("http://example.com/feed.xml", timeout=10)
    mock_asset.delete_asset.assert_called_once()
    mock_release.upload_asset.assert_called_once()


@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
@patch("src.rss.requests")
def test_existing_feed_missing_channel_raises_error(mock_requests, mock_github):
    """Test that a feed.xml with no channel element raises RuntimeError."""
    invalid_xml = b"<?xml version='1.0' encoding='utf-8'?><rss version=\"2.0\"></rss>"

    mock_asset = MagicMock()
    mock_asset.name = "feed.xml"
    mock_asset.browser_download_url = "http://example.com/feed.xml"

    mock_release = MagicMock()
    mock_release.get_assets.return_value = [mock_asset]

    mock_repo = MagicMock()
    mock_repo.get_release.return_value = mock_release

    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github.return_value = mock_github_instance

    mock_requests.get.return_value.content = invalid_xml

    with pytest.raises(RuntimeError, match="Invalid RSS feed: missing channel element"):
        update_feed(
            "Episode 1",
            "Desc",
            "Mon, 01 Jan 2024 00:00:00 +0000",
            "http://audio.mp3",
            "guid-1",
        )


@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
@patch("src.rss.requests")
def test_duplicate_guid_raises_error(mock_requests, mock_github):
    """Test that adding an episode with an already-existing guid raises RuntimeError."""
    existing_xml = _make_feed_xml(guids=["guid-1"])

    mock_asset = MagicMock()
    mock_asset.name = "feed.xml"
    mock_asset.browser_download_url = "http://example.com/feed.xml"

    mock_release = MagicMock()
    mock_release.get_assets.return_value = [mock_asset]

    mock_repo = MagicMock()
    mock_repo.get_release.return_value = mock_release

    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github.return_value = mock_github_instance

    mock_requests.get.return_value.content = existing_xml

    with pytest.raises(RuntimeError, match="already exists in feed"):
        update_feed(
            "Episode 1",
            "Desc",
            "Mon, 01 Jan 2024 00:00:00 +0000",
            "http://audio.mp3",
            "guid-1",
        )


@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
@patch("src.rss.requests")
def test_create_release_when_not_found(mock_requests, mock_github):
    """Test that a new release is created when the podcast-rss tag doesn't exist."""
    mock_release = MagicMock()
    mock_release.get_assets.return_value = []

    mock_repo = MagicMock()
    mock_repo.get_release.side_effect = GithubException(404, {"message": "Not Found"})
    mock_repo.create_git_release.return_value = mock_release

    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github.return_value = mock_github_instance

    mock_requests.head.return_value.headers = {"Content-Length": "1000"}

    update_feed(
        "Episode 1",
        "Desc",
        "Mon, 01 Jan 2024 00:00:00 +0000",
        "http://audio.mp3",
        "guid-1",
    )

    mock_repo.create_git_release.assert_called_once_with(
        tag="podcast-rss",
        name="Podcast RSS Release",
        message="Release for podcast RSS feed",
    )


@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
@patch("src.rss.requests")
@patch("src.rss.os.remove")
def test_appended_item_contains_required_tags(_mock_remove, mock_requests, mock_github):
    """Test that the appended item contains title, description, pubDate, enclosure, and guid."""
    mock_release = MagicMock()
    mock_release.get_assets.return_value = []

    mock_repo = MagicMock()
    mock_repo.get_release.return_value = mock_release

    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github.return_value = mock_github_instance

    mock_requests.head.return_value.headers = {"Content-Length": "5000"}

    update_feed(
        "Episode 1",
        "A great episode",
        "Mon, 01 Jan 2024 00:00:00 +0000",
        "http://audio.example.com/ep1.mp3",
        "guid-episode-1",
    )

    temp_path = mock_release.upload_asset.call_args[1]["path"]
    with open(temp_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    assert "<title>Episode 1</title>" in xml_content
    assert "<description>A great episode</description>" in xml_content
    assert "<pubDate>Mon, 01 Jan 2024 00:00:00 +0000</pubDate>" in xml_content
    assert "<guid>guid-episode-1</guid>" in xml_content
    assert "<enclosure" in xml_content

    os.remove(temp_path)


@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
def test_github_api_error(mock_github):
    """Test that a GitHub API error is wrapped in a RuntimeError."""
    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.side_effect = GithubException(
        401, {"message": "Unauthorized"}
    )
    mock_github.return_value = mock_github_instance

    with pytest.raises(RuntimeError, match="GitHub API error: 401"):
        update_feed(
            "Episode 1",
            "Desc",
            "Mon, 01 Jan 2024 00:00:00 +0000",
            "http://audio.mp3",
            "guid-1",
        )
