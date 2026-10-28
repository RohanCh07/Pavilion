"""Offline provider that plays a scripted match, for demos and tests without an API key.

Every call to ``fixture_details`` advances the match clock by ``minutes_per_poll``, so with
the bot running you'll see live alerts arrive on each poll until full time.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, date, datetime

from fantasy_bot.domain import (
    Fixture,
    FixtureDetails,
    PlayerInfo,
    PlayerLine,
    PlayerStats,
    Position,
)

HOME, AWAY = 1, 2
FIXTURE_ID = 1001

PLAYERS: tuple[PlayerInfo, ...] = (
    PlayerInfo(11, "David Raya", HOME, "Arsenal", Position.GOALKEEPER),
    PlayerInfo(12, "William Saliba", HOME, "Arsenal", Position.DEFENDER),
    PlayerInfo(13, "Martin Odegaard", HOME, "Arsenal", Position.MIDFIELDER),
    PlayerInfo(14, "Bukayo Saka", HOME, "Arsenal", Position.FORWARD),
    PlayerInfo(15, "Gabriel Martinelli", HOME, "Arsenal", Position.FORWARD),
    PlayerInfo(21, "Robert Sanchez", AWAY, "Chelsea", Position.GOALKEEPER),
    PlayerInfo(22, "Levi Colwill", AWAY, "Chelsea", Position.DEFENDER),
    PlayerInfo(23, "Cole Palmer", AWAY, "Chelsea", Position.MIDFIELDER),
    PlayerInfo(24, "Nicolas Jackson", AWAY, "Chelsea", Position.FORWARD),
)
STARTERS = frozenset({11, 12, 13, 14, 21, 22, 23, 24})
SUB_ON = {15: 65}  # player id -> minute he comes on

# (minute, player id, stat, amount)
SCRIPT: tuple[tuple[int, int, str, int], ...] = (
    (12, 21, "saves", 1),
    (23, 14, "goals", 1),
    (23, 13, "assists", 1),
    (31, 11, "saves", 1),
    (38, 22, "yellow_cards", 1),
    (52, 23, "penalties_missed", 1),
    (52, 11, "penalties_saved", 1),
    (70, 15, "goals", 1),
    (70, 14, "assists", 1),
    (81, 21, "saves", 1),
    (88, 22, "own_goals", 1),
)
GOAL_STATS = {"goals": False, "own_goals": True}  # stat -> counts for the other side


class MockProvider:
    def __init__(self, kickoff: datetime | None = None, minutes_per_poll: int = 15) -> None:
        self.kickoff = kickoff or datetime.now(UTC)
        self.minute = 0
        self.minutes_per_poll = minutes_per_poll

    def _fixture(self) -> Fixture:
        home = away = 0
        for minute, pid, stat, n in SCRIPT:
            if minute > self.minute or stat not in GOAL_STATS:
                continue
            scorer_home = _player(pid).team_id == HOME
            if scorer_home != GOAL_STATS[stat]:
                home += n
            else:
                away += n
        return Fixture(
            id=FIXTURE_ID,
            league_id=39,
            league_name="Premier League (demo)",
            home_id=HOME,
            home_name="Arsenal",
            away_id=AWAY,
            away_name="Chelsea",
            kickoff=self.kickoff,
            status=_status(self.minute),
            elapsed=self.minute or None,
            home_goals=home if self.minute else None,
            away_goals=away if self.minute else None,
        )

    def _details(self) -> FixtureDetails:
        fixture = self._fixture()
        conceded = {HOME: fixture.away_goals or 0, AWAY: fixture.home_goals or 0}
        lines = []
        for p in PLAYERS:
            on_at = 0 if p.id in STARTERS else SUB_ON.get(p.id)
            minutes = max(0, self.minute - on_at) if on_at is not None else 0
            stats = PlayerStats(
                minutes=minutes,
                started=p.id in STARTERS and minutes > 0,
                team_conceded=conceded[p.team_id],
            )
            for minute, pid, stat, n in SCRIPT:
                if pid == p.id and minute <= self.minute:
                    stats = replace(stats, **{stat: getattr(stats, stat) + n})
            lines.append(PlayerLine(p, stats))
        return FixtureDetails(fixture, tuple(lines))

    async def search_players(self, query: str) -> list[PlayerInfo]:
        q = query.strip().lower()
        return [p for p in PLAYERS if q and q in p.name.lower()]

    async def fixtures_on(self, day: date) -> list[Fixture]:
        return [self._fixture()] if day == self.kickoff.date() else []

    async def fixture_details(self, fixture_ids: Sequence[int]) -> list[FixtureDetails]:
        if FIXTURE_ID not in fixture_ids:
            return []
        self.minute = min(90, self.minute + self.minutes_per_poll)
        return [self._details()]

    async def last_fixture_for_team(self, team_id: int) -> Fixture | None:
        return self._fixture() if team_id in (HOME, AWAY) else None

    async def aclose(self) -> None:
        return None


def _status(minute: int) -> str:
    if minute == 0:
        return "NS"
    if minute >= 90:
        return "FT"
    if minute == 45:
        return "HT"
    return "1H" if minute < 45 else "2H"


def _player(pid: int) -> PlayerInfo:
    return next(p for p in PLAYERS if p.id == pid)
