"""Polls tracked fixtures, scores them and pushes per-user alerts.

Polling is driven by the fixture schedule rather than a blind "anything live?" loop: a
fixture is only fetched while it is inside its tracking window *and* one of its teams has a
player in someone's squad. Outside match windows the tracker makes no API calls at all.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from fantasy_bot import messages
from fantasy_bot.domain import Fixture, FixtureDetails
from fantasy_bot.live.events import diff_points
from fantasy_bot.providers import DataProvider, ProviderError
from fantasy_bot.scoring import Rules, calculate_points
from fantasy_bot.storage import Repository

log = logging.getLogger(__name__)


class Notifier(Protocol):
    async def send(self, chat_id: int, html: str) -> bool:
        """Deliver a message; return False if the user can no longer be reached."""


class LiveTracker:
    def __init__(
        self,
        provider: DataProvider,
        repo: Repository,
        rules: Rules,
        notifier: Notifier,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._provider = provider
        self._repo = repo
        self._rules = rules
        self._notifier = notifier
        self._clock = clock
        self._schedule: dict[int, Fixture] = {}

    @property
    def schedule(self) -> list[Fixture]:
        return sorted(self._schedule.values(), key=lambda f: f.kickoff)

    async def refresh_schedule(self) -> None:
        """Load yesterday's and today's fixtures (yesterday covers games crossing midnight UTC)."""
        today = self._clock().date()
        fixtures: dict[int, Fixture] = {}
        for day in (today - timedelta(days=1), today):
            try:
                for f in await self._provider.fixtures_on(day):
                    fixtures[f.id] = f
            except ProviderError:
                log.exception("Could not load fixtures for %s", day)
                return  # keep the previous schedule rather than dropping live games
        self._schedule = fixtures
        log.info("Schedule refreshed: %d fixtures in followed leagues", len(fixtures))

    async def poll(self) -> int:
        """One tracking pass. Returns the number of messages sent."""
        now = self._clock()
        candidates = [f for f in self._schedule.values() if f.in_tracking_window(now)]
        if not candidates:
            return 0
        teams = await self._repo.tracked_team_ids()
        active = [f for f in candidates if f.team_ids & teams]
        if not active:
            return 0

        try:
            details = await self._provider.fixture_details([f.id for f in active])
        except ProviderError:
            log.exception("Live poll failed")
            return 0

        sent = 0
        for d in details:
            previous = self._schedule.get(d.fixture.id)
            self._schedule[d.fixture.id] = d.fixture
            just_finished = d.fixture.is_finished and not (previous and previous.is_finished)
            sent += await self._process(d, teams, just_finished)
        return sent

    async def _process(self, details: FixtureDetails, teams: set[int], just_finished: bool) -> int:
        fixture = details.fixture
        lines = {ln.player.id: ln for ln in details.players if ln.player.team_id in teams}
        subscribers = await self._repo.subscribers(lines)
        if not subscribers:
            return 0

        watched = {m.player.id for members in subscribers.values() for m in members}
        old = await self._repo.get_snapshots(fixture.id, watched)
        new = {pid: lines[pid].stats for pid in watched if pid in lines}
        changed = {pid: st for pid, st in new.items() if st != old.get(pid)}
        changes = {
            pid: diff_points(
                old.get(pid), st, lines[pid].player.position, self._rules, fixture.format
            )
            for pid, st in changed.items()
        }
        # Persist before sending: a crash mid-send loses an alert rather than repeating it.
        await self._repo.save_snapshots(fixture.id, fixture.scoreline, changed)

        sent = 0
        for chat_id, members in subscribers.items():
            items = [(m, c) for m in members for c in changes.get(m.player.id, ())]
            if items:
                text = messages.live_update(fixture, items, self._rules)
                sent += await self._deliver(chat_id, text)
            if just_finished:
                rows = [
                    (
                        m,
                        calculate_points(
                            new[m.player.id], m.player.position, self._rules, m.role, fixture.format
                        ),
                    )
                    for m in members
                    if m.player.id in new
                ]
                if rows:
                    sent += await self._deliver(
                        chat_id, messages.full_time(fixture, rows, self._rules.sport)
                    )
        return sent

    async def _deliver(self, chat_id: int, text: str) -> int:
        if await self._notifier.send(chat_id, text):
            return 1
        await self._repo.set_alerts(chat_id, False)
        log.info("Disabled alerts for unreachable chat %s", chat_id)
        return 0
