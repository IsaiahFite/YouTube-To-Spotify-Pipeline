# YouTube → Spotify Pipeline

![CI](https://github.com/IsaiahFite/YouTube-To-Spotify-Pipeline/actions/workflows/ci.yml/badge.svg)

A pipeline that automatically publishes YouTube livestreams as podcast episodes on Spotify. When a new video is uploaded to a YouTube channel, this pipeline downloads the audio, hosts it on GitHub Releases, and updates an RSS feed that Spotify ingests automatically.

Once set up, the only manual step is uploading your video to YouTube — the rest is handled by the pipeline.

---

## How It Works

```
YouTube Data API → yt-dlp → GitHub Releases → RSS Feed → Spotify
```

1. **YouTube Data API** detects completed livestreams published after the last processed timestamp
2. **yt-dlp** downloads the audio track and converts it to MP3 via FFmpeg
3. **GitHub Releases** hosts the audio file at a permanent public URL
4. **RSS feed** is updated with a new episode entry and re-uploaded to GitHub Releases
5. **Spotify** polls the RSS feed URL and automatically picks up new episodes

---

## Architecture

The pipeline runs **locally on a residential machine** — not on GitHub Actions. This is intentional: YouTube's bot detection blocks downloads from datacenter IPs (GitHub Actions, AWS, GCP, etc.), but allows them from residential connections.

GitHub Actions is still used for **CI only** — running tests, linting, and type checking on every push and pull request.

### Key Design Decisions

- `data/processed.json` tracks the most recent processed timestamp for incremental runs
- Videos are processed oldest-first so the RSS feed builds in chronological order
- The RSS feed and audio files are both hosted on GitHub Releases under separate tags (`podcast-rss` and `podcast-audio`)
- The pipeline checks the RSS feed for existing episodes before downloading — repeat runs are fast
- Each video gets one retry before the pipeline halts loudly for maintenance

---

## Project Structure

```
src/
  youtube.py      # Fetches completed livestreams from YouTube Data API
  audio.py        # Downloads and extracts MP3 audio with yt-dlp
  hosting.py      # Uploads audio to GitHub Releases
  rss.py          # Fetches, builds, and updates the RSS feed XML
  tracker.py      # Persists processed timestamps between runs
  pipeline.py     # Orchestrates all steps end to end

tests/
  test_youtube.py
  test_audio.py
  test_hosting.py
  test_rss.py
  test_tracker.py
  test_pipeline.py
  test_integration.py   # Real service tests, run on demand only

data/
  processed.json        # Committed to repo, tracks last processed timestamp
  audio/                # Temporary staging directory, gitignored

assets/                 # Place your podcast artwork here

.github/workflows/
  ci.yml                # Runs tests, linting, and type checking on every push
  pipeline.yml          # Scheduled workflow (kept for reference)
```

---

## Setup

### Prerequisites

- Python 3.13
- FFmpeg installed locally
- Deno installed locally (for yt-dlp JS challenge solving)
- A YouTube Data API key from Google Cloud Console
- A GitHub personal access token with `repo` scope

### Installation

```bash
git clone https://github.com/IsaiahFite/YouTube-To-Spotify-Pipeline.git
cd YouTube-To-Spotify-Pipeline
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` and fill in all values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `YOUTUBE_API_KEY` | YouTube Data API v3 key |
| `YOUTUBE_CHANNEL_ID` | YouTube channel ID to monitor |
| `START_DATE` | Backfill start date in RFC 3339 format (e.g. `2024-01-01T00:00:00Z`) |
| `FFMPEG_LOCATION` | Full path to your FFmpeg executable |
| `GITHUB_TOKEN` | GitHub personal access token |
| `GITHUB_REPO` | Repository in `username/repo` format |
| `PODCAST_TITLE` | Podcast name |
| `PODCAST_DESCRIPTION` | Podcast description |
| `PODCAST_LINK` | Podcast website URL |
| `PODCAST_LANGUAGE` | Language code (e.g. `en-us`) |
| `PODCAST_IMAGE` | Public URL to podcast artwork (3000x3000px recommended) |
| `PODCAST_AUTHOR` | Podcast author name |
| `PODCAST_EMAIL` | Podcast contact email |
| `TEST_VIDEO_ID` | YouTube video ID for integration tests (optional) |

### Podcast Artwork

Spotify requires artwork that is at minimum 1400x1400px — 3000x3000px is recommended. Host your image somewhere publicly accessible and set the URL as `PODCAST_IMAGE`. Committing the image to the repo and using the raw GitHub URL is a simple option:

```
https://raw.githubusercontent.com/username/repo/main/assets/podcast-image.png
```

### Spotify Registration

Submit your RSS feed URL to [Spotify for Podcasters](https://podcasters.spotify.com) once the feed has at least one episode. The feed URL is the `browser_download_url` of your `feed.xml` asset on the `podcast-rss` GitHub Release:

```
https://github.com/username/repo/releases/download/podcast-rss/feed.xml
```

Spotify will validate the feed and begin polling it automatically for new episodes.

---

## Running the Pipeline

```bash
python -m src.pipeline
```

Run this locally after each new video is uploaded to YouTube. The pipeline will:
- Fetch any new completed livestreams since the last run
- Skip episodes already present in the RSS feed
- Download, host, and publish each new episode
- Record the processed timestamp for the next run

---

## Development

### Running Tests

```bash
task check          # Full suite: lint, type check, tests with coverage
task test           # Tests only
task lint           # Ruff lint and format check
task typecheck      # Mypy type checking
```

### Integration Tests

Integration tests hit real services and are excluded from the normal CI run. To run them locally:

```bash
# Set TEST_VIDEO_ID in your .env first
pytest tests/test_integration.py -v
```

### CI

Every push and pull request to `dev` and `main` runs the full quality suite automatically via GitHub Actions. The CI badge above reflects the current status.

---

## Roadmap

The following features are planned for future development. Contributions are welcome.

- **YouTube thumbnails** — include per-episode artwork in the RSS feed using the video's YouTube thumbnail
- **Silence trimming** — automatically strip leading silence from livestream audio using FFmpeg before uploading
- **Intro/outro music** — prepend and append configurable audio clips with crossfade
- **GUI** — a simple interface so non-technical users can run the pipeline without touching a terminal
- **Pre-download deduplication** — check the RSS feed before downloading to make repeat runs even faster

---

## Tech Stack

- **Python 3.13**
- **yt-dlp** — audio extraction from YouTube
- **YouTube Data API v3** — detecting new uploads
- **PyGithub** — GitHub Releases management
- **defusedxml / xml.etree.ElementTree** — RSS feed parsing and generation
- **GitHub Actions** — CI (testing, linting, type checking)
- **Spotify for Podcasters** — podcast distribution
- **pytest / ruff / mypy** — testing and static analysis