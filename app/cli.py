"""CLI for vizitka: commands 'get' and 'favorites'."""

import argparse
import asyncio
import json

from app.anime import fetch_and_check
from app.db import Database


def cmd_get(args: argparse.Namespace) -> int:
    """Run get command: check animevost.org, crosscheck DB, print new episodes (or JSON)."""
    db = Database(data_dir=args.data_dir)
    new_episodes = asyncio.run(fetch_and_check(db))

    if args.json:
        print(json.dumps(new_episodes, ensure_ascii=False, indent=2))
    else:
        for ep in new_episodes:
            print(f"{ep['name']}\n  {ep['url']}")
        if not new_episodes:
            print("No new episodes.")

    return 0


def cmd_favorites(args: argparse.Namespace) -> int:
    """List favorites, or add one with --add."""
    db = Database(data_dir=args.data_dir)
    if args.add:
        db.add_favorite(args.add)
        print(f"Added: {args.add}")
    elif args.list:
        for t in db.favorites:
            print(t)
    else:
        # Default: list all favorites
        for t in db.favorites:
            print(t)
    return 0


def main() -> int:
    """Parse command (get | favorites) and dispatch to the right handler."""
    parser = argparse.ArgumentParser(prog="vizitka", description="Anime update checker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # vizitka get [--json] [--data-dir DIR]
    get_parser = subparsers.add_parser("get", help="Check for new episodes and update DB")
    get_parser.add_argument("--json", action="store_true", help="Output as JSON")
    get_parser.add_argument(
        "--data-dir",
        default=None,
        help="Data directory (default: ./data or ANIME_DB_PATH)",
    )
    get_parser.set_defaults(func=cmd_get)

    # vizitka favorites [--list] [--add NAME] [--data-dir DIR]
    fav_parser = subparsers.add_parser("favorites", help="List or add favorite anime")
    fav_parser.add_argument("--list", action="store_true", help="List favorites")
    fav_parser.add_argument("--add", type=str, help="Add a favorite by name substring")
    fav_parser.add_argument(
        "--data-dir",
        default=None,
        help="Data directory (default: ./data or ANIME_DB_PATH)",
    )
    fav_parser.set_defaults(func=cmd_favorites)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
