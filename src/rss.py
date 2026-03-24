from dotenv import load_dotenv
import os
import requests
import tempfile
from github import Github
from github import GithubException
import defusedxml.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring

load_dotenv()


def update_feed(
    title: str, description: str, pub_date: str, audio_url: str, guid: str
) -> None:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_REPO = os.getenv("GITHUB_REPO")
    if not GITHUB_TOKEN or not GITHUB_REPO:
        raise RuntimeError(
            "GITHUB_TOKEN and GITHUB_REPO must be set in environment variables. Please set GITHUB_TOKEN to your GitHub personal access token and GITHUB_REPO to the repository where your RSS feed is stored."
        )
    PODCAST_TITLE = os.getenv("PODCAST_TITLE")
    PODCAST_DESCRIPTION = os.getenv("PODCAST_DESCRIPTION")
    PODCAST_LINK = os.getenv("PODCAST_LINK")
    PODCAST_LANGUAGE = os.getenv("PODCAST_LANGUAGE")
    PODCAST_IMAGE = os.getenv("PODCAST_IMAGE")
    if (
        not PODCAST_TITLE
        or not PODCAST_DESCRIPTION
        or not PODCAST_LINK
        or not PODCAST_LANGUAGE
        or not PODCAST_IMAGE
    ):
        raise RuntimeError(
            "PODCAST_TITLE, PODCAST_DESCRIPTION, PODCAST_LINK, PODCAST_LANGUAGE, and PODCAST_IMAGE must be set in environment variables. Please set these variables to the appropriate values for your podcast."
        )

    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        try:
            release = repo.get_release("podcast-rss")
        except GithubException:
            release = repo.create_git_release(
                tag="podcast-rss",
                name="Podcast RSS Release",
                message="Release for podcast RSS feed",
            )
        assets = list(release.get_assets())
        channel = None
        if any(asset.name == "feed.xml" for asset in assets):
            # Download existing RSS feed
            asset = next(asset for asset in assets if asset.name == "feed.xml")
            content = requests.get(asset.browser_download_url, timeout=10).content
            rss = ET.fromstring(content)
            channel = rss.find("channel")
            if channel is None:
                raise RuntimeError("Invalid RSS feed: missing channel element")
        else:
            # Create new RSS feed
            rss = Element("rss", version="2.0")
            channel = SubElement(rss, "channel")
            SubElement(channel, "title").text = PODCAST_TITLE
            SubElement(channel, "description").text = PODCAST_DESCRIPTION
            SubElement(channel, "link").text = PODCAST_LINK
            SubElement(channel, "language").text = PODCAST_LANGUAGE
            image = SubElement(channel, "image")
            SubElement(image, "url").text = PODCAST_IMAGE

        # Check if item with same guid already exists
        if channel.find(f"./item[guid='{guid}']") is not None:
            raise RuntimeError(f"Episode with guid {guid} already exists in feed")

        item = SubElement(channel, "item")
        SubElement(item, "title").text = title
        SubElement(item, "description").text = description
        SubElement(item, "pubDate").text = pub_date
        SubElement(item, "guid").text = guid
        enclosure = SubElement(item, "enclosure")
        enclosure.set("url", audio_url)
        enclosure.set(
            "length",
            str(requests.head(audio_url, timeout=10).headers.get("Content-Length", 0)),
        )
        enclosure.set("type", "audio/mpeg")

        # Convert XML tree to string
        xml_str = tostring(rss, encoding="utf-8", method="xml").decode("utf-8")

        # Create temporary file in data directory for updated RSS feed
        with tempfile.NamedTemporaryFile(
            suffix=".xml", mode="w", encoding="utf-8", delete=False
        ) as f:
            f.write(xml_str)
            temp_path = f.name

        # Delete existing feed before uploading new one
        if any(asset.name == "feed.xml" for asset in assets):
            asset = next(asset for asset in assets if asset.name == "feed.xml")
            asset.delete_asset()

        # Upload updated RSS feed to GitHub release
        release.upload_asset(path=temp_path, name="feed.xml", label="Podcast RSS Feed")

        os.remove(temp_path)

    except GithubException as e:
        raise RuntimeError(f"GitHub API error: {e.status} {e.data}")
