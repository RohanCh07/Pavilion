"""Run the web API: ``python -m fantasy_bot.api`` or the ``fantasy-api`` script."""

from __future__ import annotations

import logging
import sys

from fantasy_bot.config import ConfigError, Settings


def main() -> None:
    try:
        settings = Settings.from_env(require_telegram=False)
        settings.check_ruleset()
    except ConfigError as exc:
        sys.exit(f"Configuration error: {exc}\nSee .env.example.")

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    import uvicorn

    from fantasy_bot.api.app import create_app

    uvicorn.run(create_app(settings), host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()
