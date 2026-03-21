from dotenv import load_dotenv
import os
from github import Github
from github import GithubException


# local_path is the path to the audio file on the local machine
# returns the URL of the uploaded audio file on success
def upload_audio(local_path: str) -> str:
    load_dotenv()
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_REPO = os.getenv("GITHUB_REPO")
    if not GITHUB_TOKEN or not GITHUB_REPO:
        raise RuntimeError(
            "GITHUB_TOKEN and GITHUB_REPO must be set in environment variables"
        )
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        try:
            release = repo.get_release("podcast-audio")
        except GithubException:
            release = repo.create_git_release(
                tag="podcast-audio",
                name="Podcast Audio Release",
                message="Release for podcast audio files",
            )
        asset = release.upload_asset(path=local_path)
        return asset.browser_download_url
    except FileNotFoundError:
        raise RuntimeError(f"Audio file not found at path: {local_path}")
    except GithubException as e:
        raise RuntimeError(f"GitHub API error: {e.status} {e.data}")
