"""Inline keyboards and their callback-data format: "<action>:<player id>"."""

from __future__ import annotations

from collections.abc import Sequence

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from fantasy_bot.domain import PlayerInfo, Role
from fantasy_bot.storage import SquadMember

ADD, CALC, CAPTAIN, VICE, REMOVE, NOOP = "add", "calc", "cap", "vc", "rm", "noop"


def parse(data: str) -> tuple[str, int]:
    action, _, pid = data.partition(":")
    return action, int(pid or 0)


def search_results(players: Sequence[PlayerInfo], action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"{p.name} · {p.team_name}", callback_data=f"{action}:{p.id}")]
            for p in players
        ]
    )


def squad(members: Sequence[SquadMember]) -> InlineKeyboardMarkup | None:
    if not members:
        return None
    rows = []
    for m in members:
        pid = m.player.id
        rows.append(
            [
                InlineKeyboardButton(m.player.name.split()[-1][:14], callback_data=f"{NOOP}:{pid}"),
                InlineKeyboardButton(
                    "👑 C" if m.role is not Role.CAPTAIN else "✅ C",
                    callback_data=f"{CAPTAIN}:{pid}",
                ),
                InlineKeyboardButton(
                    "VC" if m.role is not Role.VICE_CAPTAIN else "✅ VC",
                    callback_data=f"{VICE}:{pid}",
                ),
                InlineKeyboardButton("✖", callback_data=f"{REMOVE}:{pid}"),
            ]
        )
    return InlineKeyboardMarkup(rows)
