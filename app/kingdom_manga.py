"""
Kingdom manga checker: monitors https://ww5.readkingdom.com/manga/kingdom/
for new chapters. When a new chapter appears, downloads all page images to disk.
"""

import json
import os
import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

KINGDOM_URL = "https://ww5.readkingdom.com/manga/kingdom/"
CHAPTER_URL_PATTERN = "https://ww5.readkingdom.com/chapter/kingdom-chapter-{}/"
# Image URLs we care about (manga pages, not ads)
IMAGE_DOMAIN = "cdn.readkingdom.com"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; VizitkaBot/1.0)"}


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def _data_dir() -> Path:
    return Path(os.getenv("ANIME_DB_PATH", _default_data_dir()))


def _last_chapter_path() -> Path:
    return _data_dir() / "kingdom_last_chapter.json"


def _downloads_dir() -> Path:
    return _data_dir() / "downloads" / "kingdom"


def load_last_chapter() -> str | None:
    """Return last seen chapter id (e.g. '869') or None."""
    path = _last_chapter_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("chapter")
    except Exception:
        return None


def save_last_chapter(chapter: str) -> None:
    """Persist last seen chapter."""
    path = _last_chapter_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"chapter": chapter}, indent=2), encoding="utf-8")


def _extract_latest_chapter(html: str) -> str | None:
    """
    Parse the manga index page and return the latest chapter id.
    Looks for links like "Kingdom Chapter 869" -> "869".
    """
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=re.compile(r"/chapter/kingdom-chapter-")):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if "Kingdom Chapter" in text or "chapter" in href.lower():
            m = re.search(r"kingdom-chapter-([\d.]+)", href, re.I)
            if m:
                return m.group(1)
    return None


def _extract_image_urls(html: str) -> list[str]:
    """Parse chapter page and return manga page image URLs (exclude ads)."""
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src:
            continue
        if src.startswith("//"):
            src = "https:" + src
        if IMAGE_DOMAIN in src and "/mangap/" in src:
            urls.append(src)
    return urls


async def fetch_latest_chapter(client: httpx.AsyncClient) -> str | None:
    """Fetch the manga index and return the latest chapter id."""
    r = await client.get(KINGDOM_URL)
    r.raise_for_status()
    return _extract_latest_chapter(r.text)


async def fetch_chapter_images(client: httpx.AsyncClient, chapter: str) -> list[str]:
    """Fetch chapter page and return list of image URLs."""
    url = CHAPTER_URL_PATTERN.format(chapter)
    r = await client.get(url)
    r.raise_for_status()
    return _extract_image_urls(r.text)


async def download_images(
    client: httpx.AsyncClient,
    image_urls: list[str],
    chapter: str,
) -> list[Path]:
    """
    Download all images to data/downloads/kingdom/chapter-{num}/
    Returns list of saved file paths.
    """
    out_dir = _downloads_dir() / f"chapter-{chapter}"
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    for i, url in enumerate(image_urls, start=1):
        ext = "jpg"
        if ".png" in url:
            ext = "png"
        elif ".webp" in url:
            ext = "webp"
        elif ".gif" in url:
            ext = "gif"
        filename = f"{i:03d}.{ext}"
        path = out_dir / filename

        try:
            r = await client.get(url)
            r.raise_for_status()
            path.write_bytes(r.content)
            saved.append(path)
        except Exception:
            pass  # Skip failed downloads

    return saved


async def check_and_download() -> dict | None:
    """
    Check for new Kingdom chapter. If found, download images and return result.
    Returns None if no new chapter, or dict with chapter, url, image_count, saved_paths.
    """
    last = load_last_chapter()
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=30.0,
        headers=HEADERS,
    ) as client:
        latest = await fetch_latest_chapter(client)
        if not latest:
            return None

        # Normalize for comparison (869 vs 869.0)
        def norm(c: str) -> str:
            return str(float(c)) if c.replace(".", "").isdigit() else c

        if last is not None and norm(latest) <= norm(last):
            return None

        # New chapter: fetch images and download
        image_urls = await fetch_chapter_images(client, latest)
        if not image_urls:
            return None

        saved = await download_images(client, image_urls, latest)
        save_last_chapter(latest)

        chapter_url = CHAPTER_URL_PATTERN.format(latest)
        return {
            "chapter": latest,
            "url": chapter_url,
            "image_count": len(image_urls),
            "saved_count": len(saved),
            "saved_dir": str(_downloads_dir() / f"chapter-{latest}"),
            "saved_paths": [str(p) for p in saved],
        }
