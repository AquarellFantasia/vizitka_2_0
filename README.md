# Vizitka

A minimal FastAPI backend with anime update tracking (similar to TelegramNotifyer).

## Features

- **Anime list in DB** – Favorites stored in `data/favorites.json`, episodes in `data/anime_db.csv`
- **`get` command** – Fetches animevost.org, checks favorite names, crosschecks with DB for already-registered episodes, and returns only new ones

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Docker](https://www.docker.com/) (for containerized runs)

## Get command (CLI)

Check for new episodes and update the DB:

```bash
uv run python -m app get
```

Output as JSON:

```bash
uv run python -m app get --json
```

With custom data directory:

```bash
uv run python -m app get --data-dir /path/to/data
```

List or add favorites:

```bash
uv run python -m app favorites          # list
uv run python -m app favorites --add "Название аниме"
```

## Run in Container

Build the image:

```bash
docker build -t vizitka .
```

Run the container:

```bash
docker run -p 8000:8000 vizitka
```

Data directory can be mounted to persist DB:

```bash
docker run -p 8000:8000 -v $(pwd)/data:/app/data vizitka
```

The API is available at http://localhost:8000.

## Run Locally (without Docker)

Install dependencies:

```bash
uv sync
```

Start the server:

```bash
uv run uvicorn app.main:app --reload
```

## Tests

```bash
uv sync
uv run pytest -v
```

## Endpoints

| Path         | Method | Description                                                                 |
|--------------|--------|-----------------------------------------------------------------------------|
| `/`          | GET    | Root greeting                                                               |
| `/health`    | GET    | Health check                                                                |
| `/anime`     | GET    | Raw anime names from animevost.org                                          |
| `/get`       | GET    | Check favorites on page, crosscheck DB, return new episodes (and update DB) |
| `/favorites` | GET    | List favorite name substrings                                                |
| `/favorites` | POST   | Add favorite (body: `{"name": "..."}`)                                      |
| `/favorites` | DELETE | Remove favorite (body: `{"name": "..."}`)                                   |
| `/kingdom/check` | GET | Check for new Kingdom chapter, download images if found                      |

## Telegram bot

The bot calls the API to list/add/delete favorites and check new episodes.

**Local run** (API must be running, e.g. on port 8000):

```bash
export TELEGRAM_BOT_TOKEN=your_bot_token
export VIZITKA_API_URL=http://localhost:8000   # optional, default
uv run python -m app.telegram_bot
```

**Commands:** `/start`, `/favorites`, `/add <name>`, `/delete <name>`, `/get`

## Docker Compose (API + bot)

Run both the API and the Telegram bot in two containers; the bot talks to the API. Data is stored in a named volume.

```bash
export TELEGRAM_BOT_TOKEN=your_bot_token
docker compose up -d
```

- API: http://localhost:8000  
- Bot: connects to Telegram and uses `http://api:8000` internally.

## Kingdom manga checker

Monitors [readkingdom.com](https://ww5.readkingdom.com/manga/kingdom/) for new chapters. When a new chapter appears:
- Downloads all page images to `data/downloads/kingdom/chapter-{num}/`
- Sends a Telegram notification (via the same bot worker)

**Manual check:** `GET http://localhost:8000/kingdom/check`

**Background:** Enable with `KINGDOM_CHECK_ENABLED=1` and `KINGDOM_CHECK_INTERVAL_SECONDS=3600` (default: every hour). Set in Docker Compose.
