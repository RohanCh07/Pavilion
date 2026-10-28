"""The dependencies handlers need, bundled so they're wired once at startup."""

from __future__ import annotations

from dataclasses import dataclass

from telegram.ext import ContextTypes

from fantasy_bot.config import Settings
from fantasy_bot.live.tracker import LiveTracker
from fantasy_bot.providers import DataProvider
from fantasy_bot.scoring import Rules
from fantasy_bot.storage import Repository


@dataclass(slots=True)
class Services:
    settings: Settings
    provider: DataProvider
    repo: Repository
    rules: Rules
    tracker: LiveTracker


def services(context: ContextTypes.DEFAULT_TYPE) -> Services:
    return context.application.bot_data["services"]
