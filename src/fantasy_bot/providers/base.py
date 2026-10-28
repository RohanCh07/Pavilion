"""The contract every data source implements, whatever the sport."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from fantasy_bot.domain import Fixture, FixtureDetails, PlayerInfo, Series


class ProviderError(RuntimeError):
    """The data source failed or rejected the request (quota, auth, outage)."""


class DataProvider(Protocol):
    """A source of fixtures and raw per-player stats. Providers never compute points.

    Football providers return ``PlayerStats`` in their lines, cricket providers
    ``CricketStats``; the scoring engine turns either into points using the ruleset.
    """

    async def search_players(self, query: str) -> list[PlayerInfo]:
        """Players in the followed competitions whose name matches ``query``."""

    async def fixtures_on(self, day: date) -> list[Fixture]:
        """Fixtures in the followed competitions on ``day`` (UTC)."""

    async def fixture_details(self, fixture_ids: Sequence[int]) -> list[FixtureDetails]:
        """Score, status and per-player stats for each fixture id."""

    async def last_fixture_for_team(self, team_id: int) -> Fixture | None:
        """The team's most recent fixture that has started (live or finished)."""

    async def aclose(self) -> None:
        """Release network resources."""


class SeriesProvider(DataProvider, Protocol):
    """A provider that also knows series (tours, tournaments, leagues), for fantasy teams."""

    async def list_series(self) -> list[Series]:
        """Current and recent series."""

    async def current_matches(self) -> list[Fixture]:
        """Live, recently finished and upcoming matches across every followed series."""

    async def series_matches(self, series_id: int) -> list[Fixture]:
        """Every match in the series, played or not, oldest first."""

    async def series_players(self, series_id: int) -> list[PlayerInfo]:
        """Every player in any squad of the series."""


def supports_series(provider: object) -> bool:
    return all(
        callable(getattr(provider, m, None))
        for m in ("list_series", "current_matches", "series_matches", "series_players")
    )


FootballProvider = DataProvider  # the original name, kept for existing imports
