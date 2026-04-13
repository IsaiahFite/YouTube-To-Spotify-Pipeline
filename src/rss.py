from dotenv import load_dotenv
import os
import requests
import tempfile
from github import Github
from github import GithubException
import defusedxml.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring

load_dotenv()


def fetch_feed() -> tuple:
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
    PODCAST_AUTHOR = os.getenv("PODCAST_AUTHOR")
    PODCAST_EMAIL = os.getenv("PODCAST_EMAIL")
    if not PODCAST_AUTHOR or not PODCAST_EMAIL:
        raise RuntimeError(
            "PODCAST_AUTHOR and PODCAST_EMAIL must be set in environment variables."
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

        if any(asset.name == "feed.xml" for asset in assets):
            asset = next(asset for asset in assets if asset.name == "feed.xml")
            content = requests.get(asset.browser_download_url, timeout=10).content
            rss = ET.fromstring(content)
            channel = rss.find("channel")
            if channel is None:
                raise RuntimeError("Invalid RSS feed: missing channel element")
        else:
            rss = Element("rss", attrib={
                "version": "2.0",
                "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"
            })
            channel = SubElement(rss, "channel")
            SubElement(channel, "title").text = PODCAST_TITLE
            SubElement(channel, "description").text = PODCAST_DESCRIPTION
            SubElement(channel, "link").text = PODCAST_LINK
            SubElement(channel, "language").text = PODCAST_LANGUAGE
            image = SubElement(channel, "image")
            SubElement(image, "url").text = PODCAST_IMAGE
            SubElement(channel, "itunes:author").text = PODCAST_AUTHOR
            owner = SubElement(channel, "itunes:owner")
            SubElement(owner, "itunes:email").text = PODCAST_EMAIL

        return rss, channel, release, assets

    except GithubException as e:
        raise RuntimeError(f"GitHub API error: {e.status} {e.data}")


def get_existing_guids(channel: Element) -> set:
    return {
        item.findtext("guid")
        for item in channel.findall("item")
        if item.findtext("guid")
    }


def update_feed(
    rss: Element,
    channel: Element,
    release,
    assets: list,
    title: str,
    description: str,
    pub_date: str,
    audio_url: str,
    guid: str,
    thumbnail_url: str = "",
) -> None:
    item = SubElement(channel, "item")
    SubElement(item, "title").text = title
    SubElement(item, "description").text = description
    SubElement(item, "pubDate").text = pub_date
    SubElement(item, "guid").text = guid
    if thumbnail_url:
        itunes_image = SubElement(item, "itunes:image")
        itunes_image.set("href", thumbnail_url)
    enclosure = SubElement(item, "enclosure")
    enclosure.set("url", audio_url)
    enclosure.set(
        "length",
        str(requests.head(audio_url, timeout=10).headers.get("Content-Length", 0)),
    )
    enclosure.set("type", "audio/mpeg")

    xml_str = tostring(rss, encoding="utf-8", method="xml").decode("utf-8")

    with tempfile.NamedTemporaryFile(
        suffix=".xml", mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(xml_str)
        temp_path = f.name

    # Delete old asset and remove from list before uploading updated feed
    if any(asset.name == "feed.xml" for asset in assets):
        old_asset = next(asset for asset in assets if asset.name == "feed.xml")
        old_asset.delete_asset()
        assets.remove(old_asset)

    new_asset = release.upload_asset(path=temp_path, name="feed.xml", label="Podcast RSS Feed")
    assets.append(new_asset)

    os.remove(temp_path)
