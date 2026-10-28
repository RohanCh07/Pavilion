"""Sends tracker alerts through Telegram."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError

log = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send(self, chat_id: int, html: str) -> bool:
        for _ in range(2):
            try:
                await self._bot.send_message(
                    chat_id, html, parse_mode=ParseMode.HTML, disable_web_page_preview=True
                )
                return True
            except RetryAfter as exc:  # flood control: wait as told, then retry once
                delay = exc.retry_after  # int in older PTB releases, timedelta in newer ones
                await asyncio.sleep(
                    delay.total_seconds() if isinstance(delay, timedelta) else float(delay)
                )
            except Forbidden:  # user blocked the bot
                return False
            except BadRequest as exc:
                if "chat not found" in str(exc).lower():
                    return False
                log.warning("Bad request sending to %s: %s", chat_id, exc)
                return True
            except TelegramError:
                log.exception("Failed to send alert to %s", chat_id)
                return True
        return True
