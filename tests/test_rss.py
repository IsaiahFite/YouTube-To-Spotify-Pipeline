import pytest
import os
from unittest.mock import patch, MagicMock
from github import GithubException
from xml.etree.ElementTree import tostring, Element, SubElement
from src.rss import fetch_feed, get_existing_guids, update_feed

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


def _make_mock_github(release):
    """Return a mock Github class whose instance yields the given release."""
    mock_repo = MagicMock()
    mock_repo.get_release.return_value = release
    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github = MagicMock(return_value=mock_github_instance)
    return mock_github, mock_repo


# ---------------------------------------------------------------------------
# fetch_feed — env var validation
# ---------------------------------------------------------------------------

@patch.dict("os.environ", {"GITHUB_TOKEN": "", "GITHUB_REPO": ""})
def test_fetch_feed_missing_github_env_vars():
    """Missing GitHub env vars raise RuntimeError."""
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN and GITHUB_REPO must be set"):
        fetch_feed()


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
def test_fetch_feed_missing_podcast_env_vars():
    """Missing podcast env vars raise RuntimeError."""
    with pytest.raises(RuntimeError, match="PODCAST_TITLE"):
        fetch_feed()


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
def test_fetch_feed_missing_author_email_env_vars():
    """Missing PODCAST_AUTHOR or PODCAST_EMAIL raises RuntimeError."""
    with pytest.raises(RuntimeError, match="PODCAST_AUTHOR and PODCAST_EMAIL must be set"):
        fetch_feed()


# ---------------------------------------------------------------------------
# fetch_feed — GitHub interactions
# ---------------------------------------------------------------------------

@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
def test_fetch_feed_creates_release_when_not_found(mock_github):
    """A new release is created when the podcast-rss tag doesn't exist."""
    mock_release = MagicMock()
    mock_release.get_assets.return_value = []

    mock_repo = MagicMock()
    mock_repo.get_release.side_effect = GithubException(404, {"message": "Not Found"})
    mock_repo.create_git_release.return_value = mock_release

    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github.return_value = mock_github_instance

    fetch_feed()

    mock_repo.create_git_release.assert_called_once_with(
        tag="podcast-rss",
        name="Podcast RSS Release",
        message="Release for podcast RSS feed",
    )


@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
def test_fetch_feed_github_api_error(mock_github):
    """A GitHub API error is wrapped in a RuntimeError."""
    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.side_effect = GithubException(
        401, {"message": "Unauthorized"}
    )
    mock_github.return_value = mock_github_instance

    with pytest.raises(RuntimeError, match="GitHub API error: 401"):
        fetch_feed()


@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
def test_fetch_feed_creates_fresh_xml_when_no_asset(mock_github):
    """When no feed.xml asset exists, fetch_feed returns a fresh XML tree."""
    mock_release = MagicMock()
    mock_release.get_assets.return_value = []
    mock_github, _ = _make_mock_github(mock_release)

    with patch("src.rss.Github", mock_github):
        rss, channel, release, assets = fetch_feed()

    assert rss is not None
    assert channel is not None
    assert channel.findtext("title") == "Test Podcast"
    assert assets == []


@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
@patch("src.rss.requests")
def test_fetch_feed_downloads_existing_feed(mock_requests, mock_github):
    """When a feed.xml asset exists, fetch_feed downloads and parses it."""
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

    rss, channel, release, assets = fetch_feed()

    mock_requests.get.assert_called_once_with("http://example.com/feed.xml", timeout=10)
    assert channel is not None
    assert len(channel.findall("item")) == 1


@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
@patch("src.rss.requests")
def test_fetch_feed_missing_channel_raises_error(mock_requests, mock_github):
    """A feed.xml with no channel element raises RuntimeError."""
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
        fetch_feed()


@patch.dict("os.environ", FULL_ENV)
@patch("src.rss.Github")
def test_fetch_feed_new_feed_contains_author_and_email(mock_github):
    """A freshly created feed includes itunes:author and itunes:email."""
    mock_release = MagicMock()
    mock_release.get_assets.return_value = []

    mock_repo = MagicMock()
    mock_repo.get_release.return_value = mock_release
    mock_github_instance = MagicMock()
    mock_github_instance.get_repo.return_value = mock_repo
    mock_github.return_value = mock_github_instance

    rss, channel, release, assets = fetch_feed()

    xml_content = tostring(rss, encoding="utf-8", method="xml").decode("utf-8")
    assert "Test Author" in xml_content
    assert "test@example.com" in xml_content


# ---------------------------------------------------------------------------
# get_existing_guids
# ---------------------------------------------------------------------------

def test_get_existing_guids_empty_channel():
    """An empty channel returns an empty set."""
    channel = Element("channel")
    assert get_existing_guids(channel) == set()


def test_get_existing_guids_with_items():
    """Returns the set of guid strings from existing items."""
    channel = Element("channel")
    for guid_text in ["guid-1", "guid-2", "guid-3"]:
        item = SubElement(channel, "item")
        SubElement(item, "guid").text = guid_text

    assert get_existing_guids(channel) == {"guid-1", "guid-2", "guid-3"}


def test_get_existing_guids_skips_items_without_guid():
    """Items with no guid element are excluded from the result."""
    channel = Element("channel")
    item_with = SubElement(channel, "item")
    SubElement(item_with, "guid").text = "guid-1"
    SubElement(channel, "item")  # no guid child

    assert get_existing_guids(channel) == {"guid-1"}


# ---------------------------------------------------------------------------
# update_feed
# ---------------------------------------------------------------------------

def _make_channel():
    """Return a bare rss + channel pair for update_feed tests."""
    rss = Element("rss", attrib={"version": "2.0"})
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "Test Podcast"
    return rss, channel


@patch("src.rss.requests")
@patch("src.rss.os.remove")
def test_update_feed_appends_item_with_required_tags(_mock_remove, mock_requests):
    """update_feed appends an item containing all required child elements."""
    rss, channel = _make_channel()
    mock_release = MagicMock()
    mock_release.upload_asset.return_value = MagicMock(name="feed.xml")
    assets = []

    mock_requests.head.return_value.headers = {"Content-Length": "5000"}

    update_feed(
        rss, channel, mock_release, assets,
        "Episode 1", "A great episode",
        "Mon, 01 Jan 2024 00:00:00 +0000",
        "http://audio.example.com/ep1.mp3",
        "guid-episode-1",
        "https://example.com/thumb.jpg",
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


@patch("src.rss.requests")
@patch("src.rss.os.remove")
def test_update_feed_uploads_to_release(_mock_remove, mock_requests):
    """update_feed calls upload_asset with the correct name and label."""
    rss, channel = _make_channel()
    mock_release = MagicMock()
    mock_release.upload_asset.return_value = MagicMock(name="feed.xml")
    assets = []

    mock_requests.head.return_value.headers = {"Content-Length": "1000"}

    update_feed(
        rss, channel, mock_release, assets,
        "Episode 1", "Desc",
        "Mon, 01 Jan 2024 00:00:00 +0000",
        "http://audio.mp3",
        "guid-1",
        "https://example.com/thumb.jpg",
    )

    call_kwargs = mock_release.upload_asset.call_args[1]
    assert call_kwargs["name"] == "feed.xml"
    assert call_kwargs["label"] == "Podcast RSS Feed"


@patch("src.rss.requests")
@patch("src.rss.os.remove")
def test_update_feed_deletes_existing_asset_before_upload(_mock_remove, mock_requests):
    """update_feed deletes the existing feed.xml asset before uploading the new one."""
    rss, channel = _make_channel()
    mock_release = MagicMock()
    mock_release.upload_asset.return_value = MagicMock()

    mock_old_asset = MagicMock()
    mock_old_asset.name = "feed.xml"
    assets = [mock_old_asset]

    mock_requests.head.return_value.headers = {"Content-Length": "1000"}

    update_feed(
        rss, channel, mock_release, assets,
        "Episode 1", "Desc",
        "Mon, 01 Jan 2024 00:00:00 +0000",
        "http://audio.mp3",
        "guid-1",
        "https://example.com/thumb.jpg",
    )

    mock_old_asset.delete_asset.assert_called_once()
    mock_release.upload_asset.assert_called_once()


@patch("src.rss.requests")
@patch("src.rss.os.remove")
def test_update_feed_mutates_assets_list(_mock_remove, mock_requests):
    """update_feed removes the old asset and appends the new one to the assets list."""
    rss, channel = _make_channel()
    mock_release = MagicMock()
    new_asset = MagicMock()
    mock_release.upload_asset.return_value = new_asset

    old_asset = MagicMock()
    old_asset.name = "feed.xml"
    assets = [old_asset]

    mock_requests.head.return_value.headers = {"Content-Length": "1000"}

    update_feed(
        rss, channel, mock_release, assets,
        "Episode 1", "Desc",
        "Mon, 01 Jan 2024 00:00:00 +0000",
        "http://audio.mp3",
        "guid-1",
        "https://example.com/thumb.jpg",
    )

    assert old_asset not in assets
    assert new_asset in assets


@patch("src.rss.requests")
@patch("src.rss.os.remove")
def test_update_feed_includes_itunes_image(_mock_remove, mock_requests):
    """update_feed appends <itunes:image> with the correct href when thumbnail_url is provided."""
    rss, channel = _make_channel()
    mock_release = MagicMock()
    mock_release.upload_asset.return_value = MagicMock(name="feed.xml")
    assets = []

    mock_requests.head.return_value.headers = {"Content-Length": "5000"}

    update_feed(
        rss, channel, mock_release, assets,
        "Episode 1", "A great episode",
        "Mon, 01 Jan 2024 00:00:00 +0000",
        "http://audio.example.com/ep1.mp3",
        "guid-episode-1",
        "https://example.com/maxres.jpg",
    )

    temp_path = mock_release.upload_asset.call_args[1]["path"]
    with open(temp_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    assert 'itunes:image' in xml_content
    assert 'href="https://example.com/maxres.jpg"' in xml_content

    os.remove(temp_path)


@patch("src.rss.requests")
@patch("src.rss.os.remove")
def test_update_feed_omits_itunes_image_when_no_thumbnail(_mock_remove, mock_requests):
    """update_feed does not append <itunes:image> when thumbnail_url is empty."""
    rss, channel = _make_channel()
    mock_release = MagicMock()
    mock_release.upload_asset.return_value = MagicMock(name="feed.xml")
    assets = []

    mock_requests.head.return_value.headers = {"Content-Length": "5000"}

    update_feed(
        rss, channel, mock_release, assets,
        "Episode 1", "A great episode",
        "Mon, 01 Jan 2024 00:00:00 +0000",
        "http://audio.example.com/ep1.mp3",
        "guid-episode-1",
    )

    temp_path = mock_release.upload_asset.call_args[1]["path"]
    with open(temp_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    assert 'itunes:image' not in xml_content

    os.remove(temp_path)
