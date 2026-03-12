"""Anime scraper and episode checker."""

import re

import httpx
from bs4 import BeautifulSoup

from app.db import Database

ANIMEVOST_URL = "https://animevost.org/"


def _get_episode_from_name(name: str) -> str | None:
    """Extract episode part from string like 'Name / [1-7 из 12]'."""
    m = re.search(r"\[([^\]]+)\]", name)
    return m.group(1) if m else None


def _get_full_name(name: str) -> str:
    """Extract anime name part from string like 'Name / [1-7 из 12]'."""
    return name.split("/")[0].strip() if "/" in name else name.strip()


def _scrape_shortstory_head(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Scrape anime from div.shortstoryHead (TelegramNotifyer style)."""
    items = []
    for div in soup.find_all("div", class_="shortstoryHead"):
        a = div.find("a")
        if not a or not a.string:
            continue
        text = a.get_text(strip=True)
        href = a.get("href", "")
        if href and text:
            items.append((text, href))
    return items


def _scrape_latest_updates(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Scrape anime from 'Последние обновления' section."""
    items = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if "Последние обновления" not in heading.get_text():
            continue
        next_list = heading.find_next(["ul", "ol"])
        if not next_list:
            continue
        for link in next_list.find_all("a", href=re.compile(r"animevost\.org/tip/")):
            text = link.get_text(strip=True)
            href = link.get("href", "")
            if text and href and len(text) > 3:
                items.append((text, href))
        break
    return items


def _scrape_fallback(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Fallback: collect anime links from page."""
    items = []
    seen = set()
    for link in soup.find_all("a", href=re.compile(r"animevost\.org/tip/(?:tv|ona|ova)/")):
        text = link.get_text(strip=True)
        href = link.get("href", "")
        if text and href and len(text) > 5 and text not in seen:
            seen.add(text)
            items.append((text, href))
            if len(items) >= 50:
                break
    return items


async def scrape_animevost(client: httpx.AsyncClient | None = None) -> list[tuple[str, str]]:
    """Fetch animevost.org and return list of (full_text, url) for anime on page."""
    async with client or httpx.AsyncClient(
        follow_redirects=True,
        timeout=15.0,
        headers={"User-Agent": "Mozilla/5.0 (compatible; VizitkaBot/1.0)"},
    ) as c:
        response = await c.get(ANIMEVOST_URL)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    items = _scrape_shortstory_head(soup)
    if not items:
        items = _scrape_latest_updates(soup)
    if not items:
        items = _scrape_fallback(soup)
    return items


def get_new_episodes(db: Database, scraped: list[tuple[str, str]]) -> list[dict]:
    """
    Filter scraped items by favorites and return those not yet registered.
    Returns list of dicts: {name, full_name, episode, url}.
    """
    result = []
    favorites = db.favorites

    for text, url in scraped:
        if not any(fav in text for fav in favorites):
            continue

        full_name = _get_full_name(text)
        episode = _get_episode_from_name(text)
        if not episode:
            continue

        if db.is_episode_registered(full_name, episode):
            continue

        registered = db.get_registered(full_name)
        if registered is None:
            db.add_anime(full_name, episode)
        else:
            db.update_episode(full_name, episode)

        result.append({
            "name": text,
            "full_name": full_name,
            "episode": episode,
            "url": url if url.startswith("http") else f"https://animevost.org{url}",
        })

    return result


async def fetch_and_check(db: Database) -> list[dict]:
    """Scrape page, crosscheck with DB, return new episodes."""
    scraped = await scrape_animevost()
    return get_new_episodes(db, scraped)
