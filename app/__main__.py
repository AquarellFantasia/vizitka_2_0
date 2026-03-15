"""Allow running the CLI as: python -m app."""

from app.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
