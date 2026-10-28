"""Builds the Telegram application and wires services, handlers and background jobs."""

from __future__ import annotations

import logging

from telegram import BotCommand
from telegram.ext import Application, ContextTypes

from fantasy_bot.bot import handlers
from fantasy_bot.bot.notifier import TelegramNotifier
from fantasy_bot.bot.services import Services, services
from fantasy_bot.config import Settings
from fantasy_bot.live.tracker import LiveTracker
from fantasy_bot.providers import build_provider
from fantasy_bot.scoring import load_rules
from fantasy_bot.storage import Repository, create_engine, init_db, session_factory

log = logging.getLogger(__name__)

COMMANDS = [
    BotCommand("team", "Your squad and latest points"),
    BotCommand("add", "Add a player to your squad"),
    BotCommand("calc", "Points from a player's latest match"),
    BotCommand("fixtures", "Today's matches"),
    BotCommand("rules", "How points are scored"),
    BotCommand("alerts", "Turn live alerts on or off"),
    BotCommand("help", "What I can do"),
]


async def _poll(context: ContextTypes.DEFAULT_TYPE) -> None:
    sent = await services(context).tracker.poll()
    if sent:
        log.info("Live poll sent %d messages", sent)


async def _refresh_schedule(context: ContextTypes.DEFAULT_TYPE) -> None:
    await services(context).tracker.refresh_schedule()


def build_application(settings: Settings) -> Application:
    engine = create_engine(settings.database_url)

    async def post_init(app: Application) -> None:
        await init_db(engine)
        provider = build_provider(settings)
        rules = load_rules(settings.scoring_ruleset)
        repo = Repository(session_factory(engine), rules.stats_type)
        tracker = LiveTracker(provider, repo, rules, TelegramNotifier(app.bot))
        app.bot_data["services"] = Services(settings, provider, repo, rules, tracker)

        await app.bot.set_my_commands(COMMANDS)
        jq = app.job_queue
        jq.run_repeating(
            _refresh_schedule, interval=settings.schedule_refresh_seconds, first=0, name="schedule"
        )
        jq.run_repeating(_poll, interval=settings.live_poll_seconds, first=15, name="live-poll")
        log.info(
            "Bot ready: sport=%s provider=%s ruleset=%s",
            settings.sport,
            settings.data_provider,
            rules.name,
        )

    async def post_shutdown(app: Application) -> None:
        if svc := app.bot_data.get("services"):
            await svc.provider.aclose()
        await engine.dispose()

    app = (
        Application.builder()
        .token(settings.telegram_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .concurrent_updates(True)
        .build()
    )
    handlers.register(app)
    return app
