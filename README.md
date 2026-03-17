# YouTube → Spotify Pipeline

![CI](https://github.com/IsaiahFite/YouTube-To-Spotify-Pipeline/actions/workflows/ci.yml/badge.svg)

Automatically converts church sermon livestreams uploaded to YouTube into Spotify podcast episodes via RSS feed generation. The only manual step is uploading to YouTube — everything else is hands-free.

---

## How It Works

1. **YouTube Data API** — detects new completed livestreams on the channel
2. **yt-dlp** — downloads the audio track from each video
3. **File hosting** — stores the audio file at a public URL (AWS S3 or GitHub Releases)
4. **RSS feed generator** — appends a new episode entry to the podcast feed XML
5. **Spotify for Podcasters** — automatically picks up new episodes from the RSS feed

The pipeline runs on a GitHub Actions cron schedule — no server required, completely free to host.

---

## Project Status

| Milestone | Description | Status |
|-----------|-------------|--------|
| 1 | Setup & Scaffolding | ✅ Complete |
| 2 | YouTube Detection | ✅ Complete |
| 3 | CI/CD Part 1 (Automated Testing) | 🔄 In Progress |
| 4 | Audio Extraction | ⬜ Not Started |
| 5 | File Hosting | ⬜ Not Started |
| 6 | RSS Feed Generation | ⬜ Not Started |
| 7 | CI/CD Part 2 (Scheduled Pipeline) | ⬜ Not Started |
| 8 | Integration Test | ⬜ Not Started |
| 9 | Spotify Registration | ⬜ Not Started |

---

## Tech Stack

- **Python 3.13**
- **YouTube Data API v3** — livestream detection
- **yt-dlp** — audio extraction
- **GitHub Actions** — CI/CD and scheduled pipeline
- **AWS S3 or GitHub Releases** — audio file hosting
- **RSS/XML** — podcast feed format
- **Spotify for Podcasters** — podcast ingestion

---

## Local Setup

### Prerequisites
- Python 3.13+
- A YouTube Data API v3 key ([get one here](https://console.cloud.google.com))

### Installation

```bash
# Clone the repo
git clone https://github.com/IsaiahFite/YouTube-To-Spotify-Pipeline.git
cd YouTube-To-Spotify-Pipeline

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```
YOUTUBE_API_KEY=your_youtube_api_key
YOUTUBE_CHANNEL_ID=your_channel_id
START_DATE=2025-01-01T00:00:00Z
```

### Running Tests

```bash
pytest --cov=src --cov-report=term-missing
```

---

## Project Structure

```
YouTube-To-Spotify-Pipeline/
├── .github/
│   └── workflows/
│       └── ci.yml
├── data/
│   └── processed.json
├── src/
│   ├── __init__.py
│   └── youtube.py
│   └── tracker.py
├── tests/
│   ├── __init__.py
│   ├── test_youtube.py
│   └── test_tracker.py
├── .env.example
├── .gitignore
├── conftest.py
└── requirements.txt
```

---

## GitHub Actions Secrets

The following secrets must be added to the repo under Settings → Secrets and variables → Actions:

| Secret | Description |
|--------|-------------|
| `YOUTUBE_API_KEY` | YouTube Data API v3 key |
| `YOUTUBE_CHANNEL_ID` | Target YouTube channel ID |
| `START_DATE` | Pipeline start date in RFC 3339 format |

---

## License

MIT