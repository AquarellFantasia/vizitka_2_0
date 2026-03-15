"""Tests for get_new_episodes logic and GET /get endpoint."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.anime import get_new_episodes
from app.db import Database


@pytest.fixture
def temp_data_dir():
    """Temporary directory for DB files; cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def db_with_favorites(temp_data_dir):
    """Database with two favorites set: Ванпанчмен, Сага о Винланде."""
    db = Database(data_dir=temp_data_dir)
    db.set_favorites(["Ванпанчмен", "Сага о Винланде"])
    return db


def test_get_new_episodes_adds_new_anime(db_with_favorites):
    """When scraped item is a favorite and episode not in DB: add to DB and return it."""
    scraped = [
        ("Ванпанчмен / [179]", "https://animevost.org/tip/tv/123"),
    ]
    result = get_new_episodes(db_with_favorites, scraped)
    assert len(result) == 1
    assert result[0]["full_name"] == "Ванпанчмен"
    assert result[0]["episode"] == "179"
    assert "animevost" in result[0]["url"]


def test_get_new_episodes_skips_registered(db_with_favorites):
    """Running twice with same scraped data: first run returns episode, second run returns nothing."""
    scraped = [
        ("Ванпанчмен / [179]", "https://animevost.org/tip/tv/123"),
    ]
    get_new_episodes(db_with_favorites, scraped)
    result2 = get_new_episodes(db_with_favorites, scraped)
    assert len(result2) == 0


def test_get_new_episodes_updates_and_returns_on_episode_change(db_with_favorites):
    """When a new episode appears for same anime: DB is updated and new episode is returned."""
    scraped1 = [("Ванпанчмен / [179]", "https://animevost.org/tip/tv/123")]
    result1 = get_new_episodes(db_with_favorites, scraped1)
    assert len(result1) == 1

    scraped2 = [("Ванпанчмен / [180]", "https://animevost.org/tip/tv/123")]
    result2 = get_new_episodes(db_with_favorites, scraped2)
    assert len(result2) == 1
    assert result2[0]["episode"] == "180"


def test_get_new_episodes_ignores_non_favorites(db_with_favorites):
    """Scraped anime that is not in favorites list is not returned or stored."""
    scraped = [
        ("Другое аниме / [1]", "https://animevost.org/tip/tv/999"),
    ]
    result = get_new_episodes(db_with_favorites, scraped)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_endpoint_returns_new_episodes():
    """GET /get returns JSON with new_episodes; we mock fetch_and_check to avoid real HTTP."""
    with patch("app.main.fetch_and_check", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [
            {"name": "Test / [1]", "full_name": "Test", "episode": "1", "url": "http://x"},
        ]
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        )
        response = await client.get("/get")
        assert response.status_code == 200
        data = response.json()
        assert "new_episodes" in data
        assert len(data["new_episodes"]) == 1
        assert data["new_episodes"][0]["full_name"] == "Test"
