"""
Telegram notifier worker.

This process consumes new-episode messages from Redis and sends them to Telegram.
It runs in a separate container from the command bot, so the bot can stay responsive.
"""

import asyncio
import json
import os
import sys

from redis.asyncio import from_url
from telegram import Bot

from app.chat_store import load_chat_ids

QUEUE_KEY = os.getenv("VIZITKA_QUEUE_KEY", "vizitka:new_episodes")
MANGA_QUEUE_KEY = os.getenv("VIZITKA_MANGA_QUEUE_KEY", "vizitka:manga_chapters")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


def _format_anime_message(payload: dict) -> str:
    full_name = payload.get("full_name") or payload.get("name") or "Anime"
    episode = payload.get("episode")
    url = payload.get("url")
    lines = [f"Новые серии: {full_name}"]
    if episode is not None:
        lines.append(f"Эпизод: {episode}")
    if url:
        lines.append(url)
    return "\n".join(lines)


def _format_manga_message(payload: dict) -> str:
    chapter = payload.get("chapter", "?")
    url = payload.get("url", "")
    count = payload.get("image_count", 0)
    lines = [f"Kingdom — новая глава {chapter}"]
    if count:
        lines.append(f"Страниц: {count}")
    if url:
        lines.append(url)
    return "\n".join(lines)


def _format_message(payload: dict) -> str:
    if payload.get("type") == "manga_chapter":
        return _format_manga_message(payload)
    return _format_anime_message(payload)


async def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Set TELEGRAM_BOT_TOKEN", file=sys.stderr)
        return 1

    # If set, notify only a single chat. Otherwise use chat_ids.json.
    chat_id_env = os.getenv("TELEGRAM_CHAT_ID")
    if chat_id_env:
        try:
            chat_ids = [int(chat_id_env)]
        except ValueError:
            chat_ids = []
    else:
        # For the multi-chat case, the user will likely call /start later.
        # Keep running even if the file doesn't exist yet; reload it as we go.
        chat_ids = []
        chat_ids_file_managed = True
    if chat_id_env:
        chat_ids_file_managed = False

    if chat_id_env and not chat_ids:
        print("Invalid TELEGRAM_CHAT_ID. It must be an integer.", file=sys.stderr)
        return 1

    bot = Bot(token=token)
    redis_client = from_url(REDIS_URL, decode_responses=True)

    while True:
        # Wait for next message from either anime or manga queue.
        item = await redis_client.blpop([QUEUE_KEY, MANGA_QUEUE_KEY], timeout=5)
        if not item:
            continue

        _, raw_payload = item
        try:
            payload = json.loads(raw_payload)
        except Exception:
            continue

        text = _format_message(payload)
        if chat_ids_file_managed:
            chat_ids = load_chat_ids()
        if not chat_ids:
            continue

        for cid in chat_ids:
            try:
                await bot.send_message(
                    chat_id=cid,
                    text=text,
                    disable_web_page_preview=True,
                )
            except Exception:
                # Don't kill the worker if one chat fails.
                continue


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        raise SystemExit(0)

