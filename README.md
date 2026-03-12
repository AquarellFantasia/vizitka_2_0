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

| Path      | Method | Description                                                                 |
|-----------|--------|-----------------------------------------------------------------------------|
| `/`       | GET    | Root greeting                                                               |
| `/health` | GET    | Health check                                                                |
| `/anime`  | GET    | Raw anime names from animevost.org                                          |
| `/get`    | GET    | Check favorites on page, crosscheck DB, return new episodes (and update DB) |
