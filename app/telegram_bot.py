"""
Telegram bot that calls the Vizitka API: list/add/delete favorites and check new episodes.
Set TELEGRAM_BOT_TOKEN and VIZITKA_API_URL (default http://localhost:8000). Run: python -m app.telegram_bot
"""

import os
import sys

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Base URL of the Vizitka API (e.g. http://api:8000 in Docker Compose)
API_BASE = os.getenv("VIZITKA_API_URL", "http://localhost:8000").rstrip("/")


async def _api_get(path: str) -> tuple[int, dict]:
    """GET from API; returns (status_code, json_or_error_dict)."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{API_BASE}{path}")
            return r.status_code, r.json() if r.content else {}
    except Exception as e:
        return 0, {"error": str(e)}


async def _api_post(path: str, json: dict) -> tuple[int, dict]:
    """POST to API; returns (status_code, json_or_error_dict)."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{API_BASE}{path}", json=json)
            return r.status_code, r.json() if r.content else {}
    except Exception as e:
        return 0, {"error": str(e)}


async def _api_delete(path: str, json: dict) -> tuple[int, dict]:
    """DELETE to API with body; returns (status_code, json_or_error_dict)."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.request("DELETE", f"{API_BASE}{path}", json=json)
            return r.status_code, r.json() if r.content else {}
    except Exception as e:
        return 0, {"error": str(e)}


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome and list commands."""
    await update.message.reply_text(
        "Привет! Я бот Vizitka.\n\n"
        "/favorites — список избранного\n"
        "/add <название> — добавить в избранное\n"
        "/delete <название> — удалить из избранного\n"
        "/get — проверить новые серии"
    )


async def cmd_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List favorites from the API."""
    code, data = await _api_get("/favorites")
    if code != 200:
        await update.message.reply_text(f"Ошибка API: {data.get('error', data)}")
        return
    favs = data.get("favorites") or []
    if not favs:
        await update.message.reply_text("Избранное пусто.")
        return
    text = "Избранное:\n" + "\n".join(f"• {f}" for f in favs)
    await update.message.reply_text(text)


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a favorite: /add <name>."""
    if not context.args:
        await update.message.reply_text("Укажите название: /add Магическая битва")
        return
    name = " ".join(context.args)
    code, data = await _api_post("/favorites", {"name": name})
    if code != 200:
        await update.message.reply_text(f"Ошибка API: {data.get('error', data)}")
        return
    await update.message.reply_text(f"Добавлено: {name}")


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a favorite: /delete <name> (exact match)."""
    if not context.args:
        await update.message.reply_text("Укажите название: /delete Магическая битва")
        return
    name = " ".join(context.args)
    code, data = await _api_delete("/favorites", {"name": name})
    if code == 404:
        await update.message.reply_text("Такого названия нет в избранном.")
        return
    if code != 200:
        await update.message.reply_text(f"Ошибка API: {data.get('error', data)}")
        return
    await update.message.reply_text(f"Удалено: {name}")


async def cmd_get(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check for new episodes via API."""
    await update.message.reply_text("Проверяю...")
    code, data = await _api_get("/get")
    if code != 200:
        await update.message.reply_text(f"Ошибка API: {data.get('error', data)}")
        return
    episodes = data.get("new_episodes") or []
    if not episodes:
        await update.message.reply_text("Новых серий нет.")
        return
    lines = [f"• {e['full_name']} — {e['episode']}\n  {e['url']}" for e in episodes]
    text = "Новые серии:\n\n" + "\n\n".join(lines)
    # Telegram message limit 4096
    if len(text) > 4000:
        text = text[:3997] + "..."
    await update.message.reply_text(text)


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Set TELEGRAM_BOT_TOKEN", file=sys.stderr)
        return 1
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("favorites", cmd_favorites))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CommandHandler("get", cmd_get))
    app.run_polling(allowed_updates=Update.ALL_TYPES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
