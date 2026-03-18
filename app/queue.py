"""
Redis-backed queue used to pass "new episode" items.

Producer: API scheduler (every 5 minutes).
Consumer: Telegram bot worker (sends messages).
"""

import json
import os
from typing import Any

from redis.asyncio import from_url, Redis

QUEUE_KEY = os.getenv("VIZITKA_QUEUE_KEY", "vizitka:new_episodes")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

_redis_client: Redis | None = None


async def _get_redis() -> Redis:
    """
    Get a cached async Redis client.
    decode_responses=True means Redis values will be returned as `str`.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = from_url(REDIS_URL, decode_responses=True)
    return _redis_client


async def enqueue_episodes(episodes: list[dict[str, Any]]) -> None:
    """Push episodes to the Redis list so another container can consume them."""
    if not episodes:
        return

    redis_client = await _get_redis()
    payloads = [json.dumps(ep, ensure_ascii=False) for ep in episodes]
    # Use RPUSH so consumer using BLPOP on the same list receives in FIFO-ish order.
    await redis_client.rpush(QUEUE_KEY, *payloads)

