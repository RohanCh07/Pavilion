"""Telegram command and button handlers. Thin: they parse input, call services, render."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from fantasy_bot import messages
from fantasy_bot.bot import keyboards as kb
from fantasy_bot.bot.services import services
from fantasy_bot.domain import PlayerInfo, Role
from fantasy_bot.providers import ProviderError
from fantasy_bot.scoring import calculate_points
from fantasy_bot.storage import AddResult

log = logging.getLogger(__name__)

HTML = {"parse_mode": ParseMode.HTML, "disable_web_page_preview": True}
SEARCH_KEY = "search_results"
SPORT_ICON = {"football": "⚽", "cricket": "🏏"}
UNAVAILABLE = "The sports data service isn't answering right now. Try again in a minute."

HELP = """{icon} <b>Fantasy Points Bot</b>

Build a squad and I'll message you live fantasy points while your players are in action.

<b>Squad</b>
/add <i>name</i> · add a player (e.g. <code>/add {example}</code>)
/team · your squad, latest points, captain and vice-captain
/alerts on|off · live alerts (on by default)

<b>Points</b>
/calc <i>name</i> · points from a player's latest match
/fixtures · today's matches I follow
/rules · how points are scored

Tip: just type a player's name to check their points."""


# General -------------------------------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await services(context).repo.upsert_user(
        update.effective_chat.id, user.username if user else None
    )
    sport = services(context).settings.sport
    text = HELP.format(icon=SPORT_ICON[sport], example=messages.EXAMPLE_PLAYER[sport])
    await update.effective_message.reply_text(text, **HTML)


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(messages.rules_text(services(context).rules), **HTML)


async def fixtures(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    svc = services(context)
    today = datetime.now(UTC).date()
    todays = [f for f in svc.tracker.schedule if f.kickoff.date() == today]
    if not todays:
        todays = await svc.provider.fixtures_on(today)
    await update.effective_message.reply_text(messages.fixtures(todays), **HTML)


async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    arg = context.args[0].lower() if context.args else ""
    if arg not in {"on", "off"}:
        await update.effective_message.reply_text("Use /alerts on or /alerts off.")
        return
    svc = services(context)
    chat_id = update.effective_chat.id
    await svc.repo.upsert_user(chat_id, update.effective_user.username)
    await svc.repo.set_alerts(chat_id, arg == "on")
    await update.effective_message.reply_text(f"Live alerts are {arg}.")


# Search -> pick flows (/add, /calc, free text) -----------------------------------------


async def _search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, action: str):
    example = messages.EXAMPLE_PLAYER[services(context).settings.sport]
    if not query:
        await update.effective_message.reply_text(
            f"Send a name with it, e.g. <code>/{action} {example}</code>", **HTML
        )
        return
    try:
        found = await services(context).provider.search_players(query)
    except ProviderError:
        log.exception("Search failed")
        await update.effective_message.reply_text(UNAVAILABLE)
        return
    if not found:
        await update.effective_message.reply_text(
            f"No players found. Use at least 4 letters of the name, e.g. <code>{example}</code>.",
            **HTML,
        )
        return
    context.user_data[SEARCH_KEY] = {p.id: p for p in found}
    verb = "add to your squad" if action == kb.ADD else "check"
    await update.effective_message.reply_text(
        f"Which player do you want to {verb}?", reply_markup=kb.search_results(found, action)
    )


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _search(update, context, " ".join(context.args), kb.ADD)


async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _search(update, context, " ".join(context.args), kb.CALC)


async def free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _search(update, context, update.effective_message.text.strip(), kb.CALC)


def _picked(context: ContextTypes.DEFAULT_TYPE, pid: int) -> PlayerInfo | None:
    return (context.user_data.get(SEARCH_KEY) or {}).get(pid)


async def _role_in_squad(context, chat_id: int, pid: int) -> Role:
    squad = await services(context).repo.get_squad(chat_id)
    return next((m.role for m in squad if m.player.id == pid), Role.PLAYER)


async def _on_add(update: Update, context: ContextTypes.DEFAULT_TYPE, player: PlayerInfo) -> None:
    svc = services(context)
    chat_id = update.effective_chat.id
    await svc.repo.upsert_user(chat_id, update.effective_user.username)
    result = await svc.repo.add_to_squad(chat_id, player, svc.settings.squad_size)
    text = {
        AddResult.ADDED: f"✅ Added {messages.player_label(player)} ({player.team_name}). "
        "Use /team to pick your captain.",
        AddResult.ALREADY_IN_SQUAD: f"{messages.player_label(player)} is already in your squad.",
        AddResult.SQUAD_FULL: f"Your squad is full ({svc.settings.squad_size}). "
        "Remove someone in /team first.",
    }[result]
    await update.callback_query.edit_message_text(text, **HTML)


async def _on_calc(update: Update, context: ContextTypes.DEFAULT_TYPE, player: PlayerInfo) -> None:
    svc = services(context)
    q = update.callback_query
    fixture = await svc.provider.last_fixture_for_team(player.team_id)
    if fixture is None:
        await q.edit_message_text(f"No recent match found for {player.team_name}.")
        return
    details = await svc.provider.fixture_details([fixture.id])
    line = details[0].line_for(player.id) if details else None
    if line is None:
        await q.edit_message_text(
            f"{messages.player_label(player)} has no stats in {messages.fixture_line(fixture)}.",
            **HTML,
        )
        return
    role = await _role_in_squad(context, update.effective_chat.id, player.id)
    result = calculate_points(
        line.stats, player.position, svc.rules, role, details[0].fixture.format
    )
    await q.edit_message_text(messages.breakdown(player, details[0].fixture, result, role), **HTML)


# Squad management ----------------------------------------------------------------------


async def _render_team(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    svc = services(context)
    members = await svc.repo.get_squad(chat_id)
    snaps = await svc.repo.latest_snapshots(m.player.id for m in members)
    rows = []
    for m in members:
        snap = snaps.get(m.player.id)
        result = (
            calculate_points(snap.stats, m.player.position, svc.rules, m.role) if snap else None
        )
        rows.append((m, result, snap.fixture_label if snap else ""))
    example = messages.EXAMPLE_PLAYER[svc.settings.sport]
    return messages.squad(rows, svc.settings.squad_size, example), kb.squad(members)


async def team(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, markup = await _render_team(update.effective_chat.id, context)
    await update.effective_message.reply_text(text, reply_markup=markup, **HTML)


async def _on_squad_action(update: Update, context, action: str, pid: int) -> None:
    repo = services(context).repo
    chat_id = update.effective_chat.id
    if action == kb.REMOVE:
        await repo.remove_from_squad(chat_id, pid)
    else:
        current = await _role_in_squad(context, chat_id, pid)
        wanted = Role.CAPTAIN if action == kb.CAPTAIN else Role.VICE_CAPTAIN
        # Tapping the role a player already holds clears it.
        await repo.set_role(chat_id, pid, Role.PLAYER if current is wanted else wanted)
    text, markup = await _render_team(chat_id, context)
    await update.callback_query.edit_message_text(text, reply_markup=markup, **HTML)


# Buttons -------------------------------------------------------------------------------


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    action, pid = kb.parse(q.data or "")
    if action == kb.NOOP:
        return
    if action in (kb.CAPTAIN, kb.VICE, kb.REMOVE):
        await _on_squad_action(update, context, action, pid)
        return

    player = _picked(context, pid)
    if player is None:
        await q.edit_message_text("That search has expired. Search again.")
        return
    try:
        await (_on_add if action == kb.ADD else _on_calc)(update, context, player)
    except ProviderError:
        log.exception("Provider failed during %s", action)
        await q.edit_message_text(UNAVAILABLE)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Unhandled error", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Something went wrong on my side. Please try again."
        )


def register(app: Application) -> None:
    for name, fn in {
        "start": start,
        "help": start,
        "rules": rules,
        "fixtures": fixtures,
        "alerts": alerts,
        "add": add,
        "calc": calc,
        "team": team,
        "myteam": team,
    }.items():
        app.add_handler(CommandHandler(name, fn))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_text))
    app.add_error_handler(on_error)
