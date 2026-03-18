"""Simple FastAPI backend."""

import asyncio
import os
import re

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.anime import fetch_and_check
from app.db import Database
from app.queue import enqueue_episodes

# --- App and config ---
app = FastAPI(title="Vizitka Backend")
ANIMEVOST_URL = "https://animevost.org/"

# Scheduler (runs in the API container, but disabled by default).
# Enable with SCHEDULER_ENABLED=1 in Docker Compose.
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "0").lower() in ("1", "true", "yes", "on")
SCHEDULER_INTERVAL_SECONDS = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "300"))


class FavoriteName(BaseModel):
    """Body for add/delete favorite: single 'name' (substring to match anime titles)."""

    name: str


async def _scheduler_loop() -> None:
    """Periodic producer loop: scrape, enqueue any new episodes to Redis."""
    while True:
        try:
            db = Database()
            new_episodes = await fetch_and_check(db)
            if new_episodes:
                await enqueue_episodes(new_episodes)
        except Exception:
            # Keep the scheduler alive even if scraping fails.
            # (For real apps, use logging instead of print.)
            pass

        await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)


@app.on_event("startup")
async def _start_scheduler() -> None:
    """Start the periodic background task if enabled."""
    if not SCHEDULER_ENABLED:
        return
    if getattr(app.state, "scheduler_task", None) is not None:
        return
    app.state.scheduler_task = asyncio.create_task(_scheduler_loop())


@app.on_event("shutdown")
async def _stop_scheduler() -> None:
    """Stop scheduler on shutdown."""
    task = getattr(app.state, "scheduler_task", None)
    if task is not None:
        task.cancel()


@app.get("/")
def root():
    """Root endpoint: returns a simple greeting."""
    return {"message": "Hello, World!"}


@app.get("/health")
def health():
    """Health check for container orchestration (e.g. Docker/K8s probes)."""
    return {"status": "ok"}


@app.get("/get")
async def get_new_episodes():
    """
    Check animevost.org for favorite anime, crosscheck with DB.
    Returns only episodes not yet registered; updates DB for new ones.
    """
    # Create DB instance (uses default data dir or ANIME_DB_PATH)
    db = Database()
    try:
        # Scrape page, filter by favorites, compare with DB, return new only
        new_episodes = await fetch_and_check(db)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch/check: {e!s}") from e
    return {"new_episodes": new_episodes}


# --- Favorites API (for Telegram bot and other clients) ---

@app.get("/favorites")
def list_favorites():
    """Return the list of favorite anime name substrings."""
    db = Database()
    return {"favorites": db.favorites}


@app.post("/favorites")
def add_favorite(body: FavoriteName):
    """Add a favorite by name substring. Idempotent if already present."""
    db = Database()
    db.add_favorite(body.name.strip())
    return {"favorites": db.favorites}


@app.delete("/favorites")
def delete_favorite(body: FavoriteName):
    """Remove a favorite by exact name match."""
    db = Database()
    if body.name.strip() not in db.favorites:
        raise HTTPException(status_code=404, detail="Favorite not found")
    db.remove_favorite(body.name.strip())
    return {"favorites": db.favorites}


@app.get("/anime")
async def get_anime_names():
    """Return names of anime from the main page of animevost.org (raw list, no DB)."""
    # Fetch the main page with a browser-like User-Agent
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; VizitkaBot/1.0)"},
        ) as client:
            response = await client.get(ANIMEVOST_URL)
            response.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch animevost.org: {e!s}")

    # Parse HTML and find the "Latest updates" block
    soup = BeautifulSoup(response.text, "html.parser")
    names = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if "Последние обновления" in heading.get_text():
            next_list = heading.find_next(["ul", "ol"])
            if next_list:
                for link in next_list.find_all("a", href=re.compile(r"animevost\.org/tip/")):
                    text = link.get_text(strip=True)
                    if text:
                        names.append(text)
            break

    # If that section wasn't found, collect any anime links from the page
    if not names:
        for link in soup.find_all("a", href=re.compile(r"animevost\.org/tip/(?:tv|ona|ova)/")):
            text = link.get_text(strip=True)
            if text and len(text) > 5 and text not in names:
                names.append(text)
                if len(names) >= 35:
                    break

    return {"anime": names}
