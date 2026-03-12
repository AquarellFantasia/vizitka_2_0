"""Simple FastAPI backend."""

import re

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException

from app.anime import fetch_and_check
from app.db import Database

app = FastAPI(title="Vizitka Backend")

ANIMEVOST_URL = "https://animevost.org/"


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Hello, World!"}


@app.get("/health")
def health():
    """Health check for container orchestration."""
    return {"status": "ok"}


@app.get("/get")
async def get_new_episodes():
    """
    Check animevost.org for favorite anime, crosscheck with DB.
    Returns only episodes not yet registered; updates DB for new ones.
    """
    db = Database()
    try:
        new_episodes = await fetch_and_check(db)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch/check: {e!s}") from e
    return {"new_episodes": new_episodes}


@app.get("/anime")
async def get_anime_names():
    """Return names of anime from the main page of animevost.org."""
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

    soup = BeautifulSoup(response.text, "html.parser")

    # Find the "Последние обновления" (Latest updates) section
    names = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if "Последние обновления" in heading.get_text():
            # Get the following list (ul/ol) and its links
            next_list = heading.find_next(["ul", "ol"])
            if next_list:
                for link in next_list.find_all("a", href=re.compile(r"animevost\.org/tip/")):
                    text = link.get_text(strip=True)
                    if text:
                        names.append(text)
            break

    if not names:
        # Fallback: collect links from first part of page matching anime pattern
        for link in soup.find_all("a", href=re.compile(r"animevost\.org/tip/(?:tv|ona|ova)/")):
            text = link.get_text(strip=True)
            if text and len(text) > 5 and text not in names:
                names.append(text)
                if len(names) >= 35:  # Approximate count in "Последние обновления"
                    break

    return {"anime": names}
