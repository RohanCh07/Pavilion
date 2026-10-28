"""Entry point: ``python -m fantasy_bot`` or the ``fantasy-bot`` script."""

from __future__ import annotations

import logging
import sys

from fantasy_bot.config import ConfigError, Settings


def main() -> None:
    try:
        settings = Settings.from_env()
        settings.check_ruleset()
    except ConfigError as exc:
        sys.exit(f"Configuration error: {exc}\nSee .env.example.")

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)  # it logs every request at INFO

    from fantasy_bot.bot.app import build_application

    build_application(settings).run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
