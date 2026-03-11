# Simple Backend

A minimal FastAPI backend that runs in Docker.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Docker](https://www.docker.com/) (for containerized runs)

## Run in Container

Build the image:

```bash
docker build -t simple-backend .
```

Run the container:

```bash
docker run -p 8000:8000 simple-backend
```

The API is available at http://localhost:8000. Try:

- http://localhost:8000/
- http://localhost:8000/health
- http://localhost:8000/docs (Swagger UI)

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

Install dependencies (includes dev/test deps):

```bash
uv sync
```

Run tests:

```bash
uv run pytest
```

Run tests with verbose output:

```bash
uv run pytest -v
```

## Endpoints

| Path     | Method | Description        |
|----------|--------|--------------------|
| `/`      | GET    | Root greeting      |
| `/health`| GET    | Health check       |
